
(function () {
  "use strict";

  const byId = (id) => document.getElementById(id);
  const state = {
    selectedFacility: "",
    selectedDeviceId: "",
    devices: [],
    facilities: [],
    refreshing: false
  };

  const assetForFamily = (family) => {
    const text = String(family || "").toLowerCase();
    if (text.indexOf("masterpact") >= 0) return "/static/actuation_devices/masterpact_mtz2.svg";
    if (text.indexOf("tesys") >= 0) return "/static/actuation_devices/tesys_island.svg";
    return "/static/actuation_devices/compact_nsx.svg";
  };

  const humanize = (value) =>
    String(value == null ? "" : value)
      .replace(/_/g, " ")
      .replace(/\s+/g, " ")
      .trim();

  const fmt = (value, digits = 1) => {
    const n = Number(value || 0);
    return n.toLocaleString(undefined, {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits
    });
  };

  const esc = (value) =>
    String(value == null ? "" : value).replace(/[&<>"']/g, (char) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;"
    }[char]));

  async function api(path, options) {
    const response = await fetch(path, options || {});
    if (!response.ok) {
      const text = await response.text();
      throw new Error(`${response.status} ${response.statusText}: ${text || path}`);
    }
    return response.json();
  }

  function showFatal(message) {
    const node = byId("fatalError");
    node.hidden = false;
    node.textContent = `Actuation Center API/UI error: ${message}`;
  }

  function clearFatal() {
    const node = byId("fatalError");
    node.hidden = true;
    node.textContent = "";
  }

  function kvRow(label, value, className) {
    return `<div class="kv-row"><span>${esc(label)}</span><strong class="${esc(className || "")}">${esc(value)}</strong></div>`;
  }

  function deviceStateClass(device) {
    if (device.communication !== "online" || device.health !== "healthy") return "warn";
    if (device.control_mode !== "remote") return "warn";
    return "";
  }

  function renderInventory(items) {
    state.devices = items;
    const count = items.length;
    byId("deviceCount").textContent = `${count} devices`;
    byId("summaryDevices").textContent = String(count);
    byId("summaryDevicesDetail").textContent = state.selectedFacility || "No facility selected";
    byId("deviceListTitle").textContent = state.selectedFacility ? `Devices · ${state.selectedFacility}` : "Devices";

    if (!count) {
      byId("devices").innerHTML = '<div class="empty-state">No actuation endpoints are registered for this facility.</div>';
      state.selectedDeviceId = "";
      renderDevice(null);
      return;
    }

    byId("devices").innerHTML = items.map((device) => {
      const active = device.device_id === state.selectedDeviceId ? " active" : "";
      const warn = deviceStateClass(device) ? " warn" : "";
      const stateLabel = device.actuation_allowed ? humanize(device.contact_state || "closed") : "protected";
      return `
        <button type="button" class="device-card${active}" data-device-id="${esc(device.device_id)}">
          <img src="${esc(assetForFamily(device.product_family))}" alt="">
          <span>
            <strong>${esc(device.device_id)}</strong>
            <span>${esc(device.product_family)}</span>
            <span>${esc(device.load_group)}</span>
          </span>
          <span class="card-state${warn}">${esc(stateLabel)}</span>
        </button>`;
    }).join("");

    byId("devices").querySelectorAll("[data-device-id]").forEach((button) => {
      button.addEventListener("click", () => {
        state.selectedDeviceId = button.getAttribute("data-device-id") || "";
        const device = state.devices.find((item) => item.device_id === state.selectedDeviceId) || null;
        renderInventory(state.devices);
        renderDevice(device);
      });
    });

    if (!state.selectedDeviceId || !items.some((item) => item.device_id === state.selectedDeviceId)) {
      const preferred = items.find((item) => item.actuation_allowed) || items[0];
      state.selectedDeviceId = preferred.device_id;
      renderInventory(items);
      renderDevice(preferred);
    }
  }

  function renderDevice(device) {
    if (!device) {
      byId("deviceId").textContent = "DEVICE";
      byId("deviceName").textContent = "Select a device";
      byId("metaFacility").textContent = "Facility · —";
      byId("metaPanel").textContent = "Panel · —";
      byId("metaLoad").textContent = "Load · —";
      byId("attachedClass").textContent = "—";
      byId("capacity").textContent = "—";
      byId("capability").textContent = "—";
      byId("manufacturer").textContent = "—";
      byId("liveState").innerHTML = "";
      return;
    }

    byId("deviceId").textContent = device.device_id || "DEVICE";
    byId("deviceName").textContent = device.product_family || "Connected device";
    byId("metaFacility").textContent = `Facility · ${device.facility_name || "—"}`;
    byId("metaPanel").textContent = `Panel · ${device.panel || "—"}`;
    byId("metaLoad").textContent = `Load · ${device.load_group || "—"}`;

    const visual = byId("deviceVisual");
    const nextAsset = assetForFamily(device.product_family);
    if (visual.getAttribute("src") !== nextAsset) {
      visual.classList.add("loading");
      visual.onload = () => visual.classList.remove("loading");
      visual.src = nextAsset;
    }

    const communication = String(device.communication || "offline").toLowerCase();
    const controlMode = String(device.control_mode || "local").toLowerCase();
    const contact = String(device.contact_state || "unknown").toLowerCase();
    const health = String(device.health || "unknown").toLowerCase();

    const commBadge = byId("commBadge");
    commBadge.textContent = communication.toUpperCase();
    commBadge.className = `badge ${communication === "online" ? "ok" : "red"}`;

    const remoteBadge = byId("remoteBadge");
    remoteBadge.textContent = controlMode.toUpperCase();
    remoteBadge.className = `badge ${controlMode === "remote" ? "ok" : "amber"}`;

    const contactBadge = byId("contactBadge");
    contactBadge.textContent = contact.toUpperCase();
    contactBadge.className = `badge ${contact === "closed" || contact === "running" ? "ok" : "amber"}`;

    const healthPill = byId("healthPill");
    healthPill.textContent = health.toUpperCase();
    healthPill.className = `status-pill ${health === "healthy" ? "ok" : "amber"}`;

    byId("screenLine1").textContent = `${communication.toUpperCase()} / ${controlMode.toUpperCase()}`;
    byId("screenLine2").textContent = `CONTACT ${contact.toUpperCase()}`;
    byId("screenLine3").textContent = device.last_command_id
      ? `Last command ${device.last_command_id}`
      : "No command received";

    byId("attachedClass").textContent = humanize(device.classification || "—").toUpperCase();
    byId("capacity").textContent = `${fmt(device.capacity_kva, 1)} kVA`;
    byId("capability").textContent = humanize(device.command_capability || "—").toUpperCase();
    byId("manufacturer").textContent = device.manufacturer || "Schneider Electric reference";

    const allowedText = device.actuation_allowed ? "YES · EMULATION" : "NO · PROTECTED";
    byId("liveState").innerHTML =
      kvRow("Contact state", contact.toUpperCase(), contact === "closed" ? "good" : "warn") +
      kvRow("Control mode", controlMode.toUpperCase(), controlMode === "remote" ? "good" : "warn") +
      kvRow("Communication", communication.toUpperCase(), communication === "online" ? "good" : "bad") +
      kvRow("Health", health.toUpperCase(), health === "healthy" ? "good" : "warn") +
      kvRow("Acknowledgement", humanize(device.ack_state || "idle").toUpperCase(), String(device.ack_state || "").indexOf("ack") >= 0 ? "good" : "") +
      kvRow("Last command", device.last_command_id || "NONE", "") +
      kvRow("Actuation allowed", allowedText, device.actuation_allowed ? "good" : "warn");
  }

  function renderGateway(status) {
    const gateway = status.gateway || {};
    const connected = String(gateway.status || "").toLowerCase() === "connected";
    const mode = humanize(status.mode || "hardware_emulation");

    byId("gateway").innerHTML =
      kvRow("Gateway status", String(gateway.status || "unknown").toUpperCase(), connected ? "good" : "warn") +
      kvRow("Mode", mode.toUpperCase(), "") +
      kvRow("Protocol", gateway.protocol || "local emulator", "") +
      kvRow("Device registry", `${status.device_count || 0} endpoints`, "") +
      kvRow("Online devices", `${status.online_devices || 0} / ${status.device_count || 0}`, "") +
      kvRow("Remote-ready", String(status.remote_ready_devices || 0), "good") +
      kvRow("Approved handoffs", String((status.approval_bridge || {}).approved_current_actions || 0), ((status.approval_bridge || {}).approved_current_actions || 0) > 0 ? "good" : "") +
      kvRow("Commands created", String((status.approval_bridge || {}).commands_created || 0), ((status.approval_bridge || {}).commands_created || 0) > 0 ? "good" : "") +
      kvRow("Rejected", String((status.approval_bridge || {}).commands_rejected || 0), ((status.approval_bridge || {}).commands_rejected || 0) > 0 ? "bad" : "good") +
      kvRow("Live electrical control", gateway.live_control_enabled ? "ENABLED" : "LOCKED", gateway.live_control_enabled ? "bad" : "good");

    byId("summaryGateway").textContent = connected ? "Connected" : "Degraded";
    byId("summaryGatewayDetail").textContent = gateway.gateway_id || "SIMBA-GW-CTRL-01";
    byId("summaryRemote").textContent = String(status.remote_ready_devices || 0);
    byId("summaryCommands").textContent = String((status.impact?.metrics || {}).approved_actions || 0);
    byId("gatewayFooter").textContent =
      `Gateway ${String(gateway.status || "unknown").toUpperCase()} · ${status.remote_ready_devices || 0} remote-ready endpoints · live switching locked`;
    byId("lastSync").textContent = gateway.last_sync_utc
      ? `${String(gateway.last_sync_utc).slice(11, 19)} UTC`
      : "not synced";
  }

  function renderEvents(items) {
    if (!items.length) {
      byId("events").innerHTML =
        '<div class="empty-state">No actuation events yet. Approve a current external recommendation to create the first emulated command.</div>';
      return;
    }

    byId("events").innerHTML = items.slice(0, 16).map((event) => {
      const detail = event.device_id || event.facility || event.command_id || event.detail || "";
      return `
        <div class="event-row">
          <div class="event-time">${esc(String(event.timestamp_utc || "").slice(11, 19) || "—")}</div>
          <div class="event-body">
            <strong>${esc(humanize(event.event || "event"))}</strong>
            <span>${esc(detail)}</span>
          </div>
        </div>`;
    }).join("");
  }

  function renderImpact(payload) {
    const metrics = payload.metrics || {};
    const restoration = metrics.next_restoration_at
      ? String(metrics.next_restoration_at).replace("T", " ").slice(0, 16)
      : Number(metrics.active_command_count || 0) > 0 ? "Pending timestamp" : "Normal state";
    const cards = [
      ["Authorised now", `${fmt(metrics.authorised_reduction_kva, 1)} kVA`],
      ["Commanded", `${fmt(metrics.commanded_reduction_kva, 1)} kVA`],
      ["Active response", `${fmt(metrics.current_reduction_kva, 1)} kVA`],
      ["Scheduled", `${Number(metrics.scheduled_command_count || 0)} command${Number(metrics.scheduled_command_count || 0) === 1 ? "" : "s"}`],
      ["Completed / restored", `${Number(metrics.completed_command_count || 0)} command${Number(metrics.completed_command_count || 0) === 1 ? "" : "s"}`],
      ["Automatic restoration", restoration]
    ];

    byId("impact").innerHTML = cards.map(([label, value]) => `
      <div class="impact-card">
        <span>${esc(label)}</span>
        <strong>${esc(value)}</strong>
      </div>`).join("");

    byId("claim").textContent =
      payload.claim_boundary ||
      "Hardware emulation only. Verified physical savings require a commissioned gateway and post-command meter response.";
  }

  async function setDeviceEmulation(communication, controlMode, health, label) {
    const device = state.devices.find((item) => item.device_id === state.selectedDeviceId);
    if (!device) return;

    const params = new URLSearchParams();
    if (communication) params.set("communication", communication);
    if (controlMode) params.set("control_mode", controlMode);
    if (health) params.set("health", health);

    const message = byId("emulatorMessage");
    message.textContent = `${label}…`;

    try {
      await api(`/api/actuation/devices/${encodeURIComponent(device.device_id)}/emulation?${params.toString()}`, {
        method: "POST"
      });
      message.textContent = `${label} applied to emulator.`;
      await refresh();
    } catch (error) {
      message.textContent = `Emulator update failed: ${error.message}`;
    }
  }

  function bindEmulatorButtons() {
    byId("btnHealthy").addEventListener("click", () =>
      setDeviceEmulation("online", "remote", "healthy", "Healthy + remote"));
    byId("btnLocal").addEventListener("click", () =>
      setDeviceEmulation("online", "local", "healthy", "Local override"));
    byId("btnOffline").addEventListener("click", () =>
      setDeviceEmulation("offline", "local", "healthy", "Offline state"));
  }

  function focusRequestedView() {
    const params = new URLSearchParams(window.location.search);
    const view = String(params.get("view") || "").toLowerCase();
    const target = {
      devices: "inventoryPanel",
      gateway: "gatewayPanel",
      logs: "logsPanel",
      settings: "settingsPanel"
    }[view];

    if (target) {
      const node = byId(target);
      if (node) {
        node.scrollIntoView({ behavior: "smooth", block: "start" });
        node.style.outline = "2px solid #1597ff";
        setTimeout(() => { node.style.outline = ""; }, 1400);
      }
    }
  }

  async function refresh() {
    if (state.refreshing) return;
    state.refreshing = true;

    try {
      clearFatal();
      const [status, facilitiesPayload, eventsPayload, impactPayload] = await Promise.all([
        api("/api/actuation/status"),
        api("/api/actuation/facilities"),
        api("/api/actuation/logs?limit=100"),
        api("/api/actuation/impact")
      ]);

      const facilities = facilitiesPayload.items || [];
      state.facilities = facilities;

      if (!state.selectedFacility || facilities.indexOf(state.selectedFacility) < 0) {
        state.selectedFacility = facilities[0] || "";
      }

      const facilitySelect = byId("facility");
      const currentOptions = Array.from(facilitySelect.options).map((option) => option.value);
      if (currentOptions.join("|") !== facilities.join("|")) {
        facilitySelect.innerHTML = facilities.map((facility) =>
          `<option value="${esc(facility)}">${esc(facility)}</option>`).join("");
      }
      facilitySelect.value = state.selectedFacility;

      const devicePayload = state.selectedFacility
        ? await api(`/api/actuation/devices?facility=${encodeURIComponent(state.selectedFacility)}`)
        : { items: [] };

      renderInventory(devicePayload.items || []);
      renderGateway(status);
      renderEvents(eventsPayload.items || []);
      renderImpact(impactPayload);
    } catch (error) {
      showFatal(error.message);
      byId("gatewayFooter").textContent = `Gateway/API error · ${error.message}`;
    } finally {
      state.refreshing = false;
    }
  }

  function init() {
    byId("facility").addEventListener("change", () => {
      state.selectedFacility = byId("facility").value;
      state.selectedDeviceId = "";
      refresh();
    });

    bindEmulatorButtons();
    refresh().then(() => setTimeout(focusRequestedView, 60));
    window.setInterval(refresh, 1200);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
}());
