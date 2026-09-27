const chat = document.getElementById("chat");
const input = document.getElementById("message");
const sendButton = document.getElementById("send");
let replyFor = null;

function bubble(kind, text) {
  const node = document.createElement("div");
  node.className = `bubble ${kind}`;
  node.textContent = text;
  chat.appendChild(node);
  chat.scrollTop = chat.scrollHeight;
}

async function loadBot() {
  const pyodide = await loadPyodide();
  pyodide.FS.mkdirTree("/app/bot");
  for (const name of ["__init__.py", "menu.py", "replies.py"]) {
    const response = await fetch(`bot/${name}`);
    if (!response.ok) throw new Error(`bot/${name}: HTTP ${response.status}`);
    pyodide.FS.writeFile(`/app/bot/${name}`, await response.text());
  }
  pyodide.runPython("import sys; sys.path.insert(0, '/app')");
  pyodide.runPython("from bot.replies import Orders, reply_for; orders = Orders()");
  const fn = pyodide.globals.get("reply_for");
  const orders = pyodide.globals.get("orders");
  replyFor = (text) => fn(text, "web-user", orders).toJs();
}

function send(text) {
  text = text.trim();
  if (!text || !replyFor) return;
  bubble("user", text);
  for (const reply of replyFor(text)) bubble("bot", reply);
}

document.getElementById("composer").addEventListener("submit", (event) => {
  event.preventDefault();
  send(input.value);
  input.value = "";
  input.focus();
});

for (const button of document.querySelectorAll(".quick button")) {
  button.addEventListener("click", () => send(button.dataset.text));
}

loadBot().then(() => {
  document.getElementById("loading").textContent = "機器人已上線，輸入「菜單」開始點餐";
  input.disabled = false;
  sendButton.disabled = false;
  input.focus();
}).catch((error) => {
  document.getElementById("loading").textContent = `載入失敗：${error}`;
});
