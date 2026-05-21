import * as React from "react";
import {
  definePlugin,
  PanelSection,
  PanelSectionRow,
  ToggleField,
  Field,
  Dropdown,
  Spinner,
  ServerAPI,
  staticClasses,
} from "decky-frontend-lib";
import { useState, useEffect, useRef, VFC } from "react";
import { FaShieldAlt } from "react-icons/fa";

interface Status {
  connected: boolean;
  interface: string | null;
  interfaces: string[];
}

const Content: VFC<{ serverAPI: ServerAPI }> = ({ serverAPI }) => {
  const [status, setStatus] = useState<Status>({ connected: false, interface: null, interfaces: [] });
  const [configs, setConfigs] = useState<string[]>([]);
  const [activeConf, setActiveConf] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [toggling, setToggling] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const togglingRef = useRef(false);

  const fetchStatus = async () => {
    if (togglingRef.current) return;
    const res = await serverAPI.callPluginMethod<{}, Status>("get_status", {});
    if (res.success) {
      setStatus({
        connected: res.result.connected,
        interface: res.result.interface ?? null,
        interfaces: res.result.interfaces ?? [],
      });
    }
  };

  const fetchConfigs = async () => {
    const res = await serverAPI.callPluginMethod<{}, string[]>("get_configs", {});
    if (res.success) {
      setConfigs(res.result);
      setActiveConf((prev) => {
        if (prev && res.result.includes(prev)) return prev;
        return res.result[0] ?? "";
      });
    }
  };

  useEffect(() => {
    // Only gate the initial spinner on get_configs (fast — just listdir).
    // Status fetch runs in parallel and updates whenever it returns; the UI
    // shouldn't block on it because `awg show` can briefly hang while the
    // userspace amneziawg-go daemon is coming up after a connect.
    fetchConfigs().finally(() => setLoading(false));
    fetchStatus();
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  // If a VPN is already up, prefer its config as the active one (matched by iface name).
  useEffect(() => {
    if (!status.interface) return;
    const match = configs.find((c) => c.replace(/\.conf$/, "") === status.interface);
    if (match && match !== activeConf) setActiveConf(match);
  }, [status.interface, configs]);

  const handleToggle = async (checked: boolean) => {
    if (!activeConf) return;
    setToggling(true);
    togglingRef.current = true;
    setError(null);
    const method = checked ? "connect" : "disconnect";
    const res = await serverAPI.callPluginMethod<{ conf: string }, { ok: boolean; error?: string }>(
      method,
      { conf: activeConf },
    );
    if (res.success && res.result.ok) {
      // Optimistic update before next poll
      setStatus((s) => ({ ...s, connected: checked, interface: checked ? activeConf.replace(/\.conf$/, "") : null }));
    } else {
      const msg = res.success ? res.result.error : "Plugin call failed";
      setError(msg ?? "Unknown error");
    }
    togglingRef.current = false;
    setToggling(false);
    await fetchStatus();
  };

  if (loading) {
    return (
      <PanelSection>
        <PanelSectionRow>
          <div style={{ display: "flex", justifyContent: "center", padding: "16px" }}>
            <Spinner />
          </div>
        </PanelSectionRow>
      </PanelSection>
    );
  }

  const statusColor = status.connected ? "#4ade80" : "#94a3b8";
  const statusText = status.connected
    ? `Подключено${status.interface ? ` (${status.interface})` : ""}`
    : "Отключено";

  const dropdownOptions = configs.map((c) => ({ data: c, label: c }));

  return (
    <PanelSection title="AmneziaWG VPN">
      <PanelSectionRow>
        <Field
          label="Статус"
          description={
            <span style={{ color: statusColor, fontWeight: 600 }}>{statusText}</span>
          }
        />
      </PanelSectionRow>

      {status.interfaces.length > 1 && (
        <PanelSectionRow>
          <Field
            label="Активные"
            description={
              <span style={{ color: "#94a3b8", fontSize: "12px" }}>
                {status.interfaces.join(", ")}
              </span>
            }
          />
        </PanelSectionRow>
      )}

      <PanelSectionRow>
        <ToggleField
          label={
            toggling
              ? (status.connected ? "Отключаюсь…" : "Подключаюсь…")
              : (status.connected ? "Выключить VPN" : "Включить VPN")
          }
          checked={status.connected}
          disabled={toggling || !activeConf}
          onChange={handleToggle}
        />
      </PanelSectionRow>

      {configs.length > 1 ? (
        <PanelSectionRow>
          <Field
            label="Конфиг"
            childrenContainerWidth="max"
            description={
              <Dropdown
                rgOptions={dropdownOptions}
                selectedOption={activeConf}
                onChange={(opt) => setActiveConf(opt.data)}
                disabled={toggling || status.connected}
              />
            }
          />
        </PanelSectionRow>
      ) : activeConf ? (
        <PanelSectionRow>
          <Field
            label="Конфиг"
            description={
              <span style={{ color: "#94a3b8", fontSize: "12px" }}>{activeConf}</span>
            }
          />
        </PanelSectionRow>
      ) : null}

      {configs.length === 0 && (
        <PanelSectionRow>
          <Field
            label=""
            description={
              <span style={{ color: "#f87171", fontSize: "12px" }}>
                Нет конфигов в /etc/amnezia/amneziawg/
              </span>
            }
          />
        </PanelSectionRow>
      )}

      {error && (
        <PanelSectionRow>
          <Field
            label=""
            description={
              <span style={{ color: "#f87171", fontSize: "12px" }}>Ошибка: {error}</span>
            }
          />
        </PanelSectionRow>
      )}
    </PanelSection>
  );
};

export default definePlugin((serverApi: ServerAPI) => {
  return {
    title: <div className={staticClasses.Title}>AmneziaWG</div>,
    content: <Content serverAPI={serverApi} />,
    icon: <FaShieldAlt />,
    onDismount() {},
  };
});
