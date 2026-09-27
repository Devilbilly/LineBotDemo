"""Issue #3: the online simulator (index.html on GitHub Pages) failed to load.

Reproduce (before the fix): open https://devilbilly.github.io/LineBotDemo/ and the
page shows

    PythonError: ... File "/app/bot/__init__.py", line 14
    .container { margin: 50px auto 40px auto; width: 600px; text-align: center; }
    SyntaxError: invalid decimal literal

Root cause: Pages builds this repo from main:/ with the legacy Jekyll builder, and
Jekyll does not publish files whose names start with "_". So bot/__init__.py was a
404, and web/chat.js wrote GitHub's HTML 404 page into Pyodide's file system as
Python source without checking the HTTP status. Line 14 of that page is the CSS
in the error.

The fix has two parts, locked here:
  * .nojekyll at the repository root, so Pages publishes the tree as it is;
  * web/chat.js stops at the first failed fetch and names the file and status,
    instead of handing an error page to Python.

The tests drive the real web/chat.js in Node (``vm``) with stand-ins for the DOM,
Pyodide and fetch. The stand-in site serves what Pages publishes, using Jekyll's
rule for underscore/dot names unless .nojekyll exists. The files chat.js writes
into the stand-in Pyodide file system are then run with CPython, using the exact
statements chat.js passes to runPython.
"""

import ast
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from bot.replies import Orders, reply_for

REPO = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
PAGES_404 = (FIXTURES / "github_pages_404.html").read_text(encoding="utf-8")
BOT_FILES = ["bot/__init__.py", "bot/menu.py", "bot/replies.py"]
MENU = "\u83dc\u55ae"
FS_ROOT = "/app"

NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="Node.js is needed to run web/chat.js")

HARNESS = r"""
const fs = require("fs");
const vm = require("vm");
const input = JSON.parse(fs.readFileSync(0, "utf8"));
const source = fs.readFileSync(input.script, "utf8");

function element() {
  return {textContent: "", disabled: true, value: "", dataset: {}, scrollTop: 0,
          scrollHeight: 0, addEventListener() {}, appendChild() {}, focus() {}};
}

async function run(scenario) {
  const log = {fetched: [], writes: {}, ran: []};
  const elements = {};
  const document = {
    getElementById: (id) => (elements[id] ??= element()),
    querySelectorAll: () => [],
    createElement: () => element(),
  };
  const pyodide = {
    FS: {mkdirTree() {}, writeFile(path, data) { log.writes[path] = data; }},
    runPython(code) { log.ran.push(code); },
    globals: {get: () => () => ({toJs: () => []})},
  };
  async function fetch(url) {
    log.fetched.push(url);
    if (url === scenario.offline) throw new TypeError("Failed to fetch");
    const [status, body] = scenario.site[url] ?? [404, scenario.notFound];
    return {status, ok: status >= 200 && status < 300, text: async () => body};
  }
  const context = vm.createContext({document, fetch, loadPyodide: async () => pyodide});
  vm.runInContext(source, context, {filename: "web/chat.js"});
  for (let i = 0; i < 5; i++) await new Promise((done) => setTimeout(done, 0));
  log.loading = document.getElementById("loading").textContent;
  log.inputDisabled = document.getElementById("message").disabled;
  return log;
}

(async () => {
  const results = {};
  for (const [name, scenario] of Object.entries(input.scenarios)) results[name] = await run(scenario);
  process.stdout.write(JSON.stringify(results));
})();
"""


def published(rel, nojekyll):
    """Whether GitHub Pages' legacy (Jekyll) build serves `rel` from the source root."""
    if nojekyll:
        return True
    return not any(part[0] in "._#" or part.endswith("~") for part in rel.split("/"))


def pages_site(nojekyll=None):
    """The static site Pages publishes: relative path -> [status, body]."""
    if nojekyll is None:
        nojekyll = (REPO / ".nojekyll").is_file()
    files = [REPO / "index.html", *REPO.glob("web/*"), *REPO.glob("bot/*.py")]
    site = {}
    for path in files:
        rel = path.relative_to(REPO).as_posix()
        if published(rel, nojekyll):
            site[rel] = [200, path.read_text(encoding="utf-8")]
    return site


def with_file(site, rel, status, body):
    return {**site, rel: [status, body]}


SCENARIOS = {
    "pages": {"site": pages_site()},
    "jekyll": {"site": pages_site(nojekyll=False)},
    "init_404": {"site": with_file(pages_site(True), "bot/__init__.py", 404, PAGES_404)},
    "replies_500": {"site": with_file(pages_site(True), "bot/replies.py", 500, "Internal Server Error")},
    "menu_404": {"site": with_file(pages_site(True), "bot/menu.py", 404, PAGES_404)},
    "offline": {"site": pages_site(True), "offline": "bot/menu.py"},
}


@pytest.fixture(scope="module")
def loads():
    payload = {
        "script": str(REPO / "web" / "chat.js"),
        "scenarios": {name: {"notFound": PAGES_404, **s} for name, s in SCENARIOS.items()},
    }
    out = subprocess.run([NODE, "-e", HARNESS], input=json.dumps(payload), capture_output=True,
                         text=True, encoding="utf-8", timeout=30, check=True)
    return json.loads(out.stdout)


def run_like_pyodide(load, tmp_path):
    """Write chat.js's files under tmp_path and run its runPython statements with CPython."""
    tmp_path = Path(tmp_path)
    for path, data in load["writes"].items():
        target = tmp_path / path.lstrip("/")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(data, encoding="utf-8")
    root = str(tmp_path / FS_ROOT.lstrip("/"))
    ran = [code.replace(repr(FS_ROOT), repr(root)) for code in load["ran"]]
    script = (
        "import json, sys\n"
        "ns = {}\n"
        "for code in json.loads(sys.argv[1]): exec(code, ns)\n"
        "print(json.dumps(ns['reply_for'](sys.argv[2], 'web-user', ns['orders'])))\n"
    )
    return subprocess.run([sys.executable, "-I", "-c", script, json.dumps(ran), MENU],
                          capture_output=True, text=True, cwd=tmp_path, timeout=30)


def test_the_published_simulator_loads_and_answers_like_the_real_bot(loads):
    load = loads["pages"]
    assert load["inputDisabled"] is False, f"the simulator did not become ready: {load['loading']}"
    with tempfile.TemporaryDirectory() as tmp:
        result = run_like_pyodide(load, tmp)
    assert result.returncode == 0, f"the loaded bot does not run: {result.stderr}"
    assert json.loads(result.stdout) == reply_for(MENU, "web-user", Orders())


def test_the_github_404_page_is_the_error_the_user_saw():
    with pytest.raises(SyntaxError) as raised:
        compile(PAGES_404, "/app/bot/__init__.py", "exec")
    assert raised.value.msg == "invalid decimal literal"
    assert raised.value.lineno == 14
    assert raised.value.text.strip() == (
        ".container { margin: 50px auto 40px auto; width: 600px; text-align: center; }")


def test_nojekyll_sits_at_the_pages_source_root():
    assert (REPO / ".nojekyll").is_file(), "Pages (source main:/) runs Jekyll without .nojekyll"


def test_every_fetched_file_is_served_byte_identical(loads):
    load = loads["pages"]
    assert load["fetched"] == BOT_FILES
    for rel in BOT_FILES:
        served = load["writes"][f"{FS_ROOT}/{rel}"]
        assert served == (REPO / rel).read_text(encoding="utf-8"), f"{rel} differs from the repo"
    assert MENU in load["writes"][f"{FS_ROOT}/bot/replies.py"]


def test_the_fetch_list_covers_every_module_the_bot_imports(loads):
    needed, todo = {"__init__"}, ["replies"]
    while todo:
        name = todo.pop()
        needed.add(name)
        tree = ast.parse((REPO / "bot" / f"{name}.py").read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.level == 1 and node.module:
                if node.module not in needed:
                    todo.append(node.module)
    assert {f"bot/{n}.py" for n in needed} <= set(loads["pages"]["fetched"])


def test_the_page_and_its_assets_are_published():
    site = pages_site()
    html = site["index.html"][1]
    local = [ref for ref in re.findall(r'(?:src|href)="([^"]+)"', html) if "://" not in ref]
    assert local, "index.html references no local assets"
    for ref in local:
        assert site.get(ref, [404])[0] == 200, f"{ref} is not published"


def test_an_empty_file_is_served_not_rejected(loads):
    assert (REPO / "bot" / "__init__.py").read_text(encoding="utf-8") == ""
    load = loads["pages"]
    assert load["writes"][f"{FS_ROOT}/bot/__init__.py"] == ""
    assert load["inputDisabled"] is False


def test_without_nojekyll_the_loader_names_the_missing_file(loads):
    load = loads["jekyll"]
    assert "bot/__init__.py: HTTP 404" in load["loading"], "the loader must name the missing file"
    assert load["ran"] == [] and load["inputDisabled"] is True


def test_a_404_never_reaches_python(loads):
    load = loads["init_404"]
    assert not any("<html" in data for data in load["writes"].values()), \
        "an HTTP error page must never be written as Python source"
    assert load["ran"] == []
    assert "bot/__init__.py: HTTP 404" in load["loading"]
    assert load["inputDisabled"] is True


def test_a_server_error_on_the_last_file_is_reported(loads):
    load = loads["replies_500"]
    assert "bot/replies.py: HTTP 500" in load["loading"], "a 500 must be reported with its status"
    assert f"{FS_ROOT}/bot/replies.py" not in load["writes"]
    assert load["ran"] == [] and load["inputDisabled"] is True


def test_the_loader_stops_at_the_first_missing_file(loads):
    load = loads["menu_404"]
    assert load["fetched"] == ["bot/__init__.py", "bot/menu.py"], "loading must stop at the first failure"
    assert "bot/menu.py: HTTP 404" in load["loading"]


def test_a_network_error_is_reported_not_marked_ready(loads):
    load = loads["offline"]
    assert "Failed to fetch" in load["loading"]
    assert load["ran"] == [] and load["inputDisabled"] is True
