document.addEventListener("DOMContentLoaded", async () => {
  const enabled = document.getElementById("enabled");
  const endpoint = document.getElementById("endpoint");
  const token = document.getElementById("token");
  const projectId = document.getElementById("projectId");
  const status = document.getElementById("status");

  const config = await chrome.runtime.sendMessage({ type: "getSettings" });
  enabled.checked = config.enabled;
  endpoint.value = config.endpoint;
  token.value = config.token;
  projectId.value = config.projectId;
  render();

  document.getElementById("save").addEventListener("click", async () => {
    await chrome.runtime.sendMessage({
      type: "saveSettings",
      settings: {
        enabled: enabled.checked,
        endpoint: endpoint.value.trim().replace(/\/$/, ""),
        token: token.value.trim(),
        projectId: projectId.value.trim() || "default"
      }
    });
    status.textContent = "Saved";
    setTimeout(render, 800);
  });

  enabled.addEventListener("change", render);
  function render() {
    status.textContent = enabled.checked ? "Capture enabled" : "Capture is off";
  }
});
