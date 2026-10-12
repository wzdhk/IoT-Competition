const $ = (id) => document.getElementById(id);

function update(data) {
  $("conn").textContent = data.conn || "已连接";
  $("conn").classList.toggle("on", !data.error);
  $("total").textContent = data.total;
  $("ok").textContent = data.ok;
  $("rate").textContent = data.rate + "%";

  const rows = (data.recent || []).map(r =>
    `<tr><td>${r.qr}</td><td><span class="tag ${r.result.toLowerCase()}">${r.result}</span></td><td>${r.time}</td></tr>`
  ).join("");
  $("records").innerHTML = rows;

  $("status").innerHTML = (data.status || []).map(s => `<li>${s}</li>`).join("");
}

window.chrome.webview.addEventListener("message", (e) => update(e.data));
window.chrome.webview.postMessage({ type: "hello" });
