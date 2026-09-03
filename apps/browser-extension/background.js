const DEFAULTS = {
  enabled: false,
  endpoint: "http://127.0.0.1:8765",
  projectId: "default",
  token: ""
};

async function settings() {
  return chrome.storage.local.get(DEFAULTS);
}

function safePage(urlString) {
  try {
    const url = new URL(urlString);
    if (!["http:", "https:"].includes(url.protocol)) return null;
    return `${url.origin}${url.pathname}`;
  } catch {
    return null;
  }
}

async function capture(type, tab) {
  const config = await settings();
  if (!config.enabled || !config.token) return;
  const url = safePage(tab.url || "");
  if (!url) return;

  const payload = {
    project_id: config.projectId,
    event_type: type,
    data: { url, title: tab.title || "", app: "browser" },
    text_content: tab.title || null,
    timestamp: new Date().toISOString()
  };

  try {
    const response = await fetch(`${config.endpoint.replace(/\/$/, "")}/api/ingest/event`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${config.token}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    });
    if (!response.ok) console.warn(`Neural Memory rejected an event: HTTP ${response.status}`);
  } catch (error) {
    console.warn("Neural Memory is unavailable", error);
  }
}

chrome.tabs.onActivated.addListener(async ({ tabId }) => capture("tab_focus", await chrome.tabs.get(tabId)));
chrome.tabs.onUpdated.addListener((_tabId, changeInfo, tab) => {
  if (changeInfo.status === "complete" && tab.active) capture("page_load", tab);
});

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message.type === "getSettings") {
    settings().then(sendResponse);
    return true;
  }
  if (message.type === "saveSettings") {
    chrome.storage.local.set(message.settings).then(() => sendResponse({ success: true }));
    return true;
  }
  return false;
});
