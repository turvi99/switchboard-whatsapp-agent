import { useCallback, useEffect, useRef, useState } from "react";
import { AlertCircle, TerminalSquare } from "lucide-react";
import ConsoleHeader from "./components/ConsoleHeader";
import TenantRail from "./components/TenantRail";
import SessionList from "./components/SessionList";
import ChatThread from "./components/ChatThread";
import BroadcastDrawer from "./components/BroadcastDrawer";
import { api } from "./api/client";
import { useLiveUpdates } from "./hooks/useLiveUpdates";

export default function App() {
  const [tenants, setTenants] = useState([]);
  const [tenantsLoading, setTenantsLoading] = useState(true);
  const [bootError, setBootError] = useState(null);

  const [selectedTenant, setSelectedTenant] = useState(null);
  const [stats, setStats] = useState(null);

  const [sessions, setSessions] = useState([]);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState(null);
  const [selectedSession, setSelectedSession] = useState(null);

  const [messages, setMessages] = useState([]);
  const [liveEvent, setLiveEvent] = useState(null);
  const [broadcastOpen, setBroadcastOpen] = useState(false);

  const refreshTimer = useRef(null);

  // ---- Initial tenant load -------------------------------------------------
  useEffect(() => {
    (async () => {
      try {
        const list = await api.listTenants();
        setTenants(list);
        if (list.length > 0) setSelectedTenant(list[0]);
      } catch (err) {
        setBootError(err.message || "Couldn't reach the backend.");
      } finally {
        setTenantsLoading(false);
      }
    })();
  }, []);

  // ---- Sessions + stats for the active tenant -------------------------------
  const refreshSessions = useCallback(async () => {
    if (!selectedTenant) return [];
    setSessionsLoading(true);
    try {
      const [list, s] = await Promise.all([
        api.listSessions(selectedTenant.tenant_id, statusFilter || undefined),
        api.getTenantStats(selectedTenant.tenant_id),
      ]);
      setSessions(list);
      setStats(s);
      return list;
    } catch {
      return [];
    } finally {
      setSessionsLoading(false);
    }
  }, [selectedTenant, statusFilter]);

  useEffect(() => {
    setSelectedSession(null);
    setMessages([]);
    refreshSessions();
  }, [selectedTenant, statusFilter, refreshSessions]);

  // ---- Messages for the active session --------------------------------------
  const refreshMessages = useCallback(async () => {
    if (!selectedTenant || !selectedSession) return;
    try {
      const list = await api.listMessages(selectedTenant.tenant_id, selectedSession.session_id);
      setMessages(list);
    } catch {
      // leave previous messages in place on transient failure
    }
  }, [selectedTenant, selectedSession]);

  useEffect(() => {
    refreshMessages();
  }, [refreshMessages]);

  // ---- Live updates -----------------------------------------------------------
  const handleWsEvent = useCallback(
    (evt) => {
      if (evt.event === "pipeline_update") {
        setLiveEvent(evt.data);
        clearTimeout(refreshTimer.current);
        refreshTimer.current = setTimeout(() => {
          if (evt.data.tenant_id === selectedTenant?.tenant_id) {
            refreshSessions();
            if (evt.data.session_id === selectedSession?.session_id) refreshMessages();
          }
        }, 250);
      } else if (evt.event === "broadcast_sent") {
        if (evt.data.tenant_id === selectedTenant?.tenant_id) refreshSessions();
      }
    },
    [selectedTenant, selectedSession, refreshSessions, refreshMessages]
  );
  const { connected } = useLiveUpdates(handleWsEvent);

  // ---- New test conversation from the empty state ---------------------------
  async function handleNewConversation(phone) {
    const list = await refreshSessions();
    const found = list.find((s) => s.customer_phone === phone);
    if (found) setSelectedSession(found);
  }

  if (tenantsLoading) {
    return (
      <div className="h-screen w-screen flex items-center justify-center bg-ink">
        <p className="text-faint text-sm font-mono">Loading console…</p>
      </div>
    );
  }

  if (bootError) {
    return (
      <div className="h-screen w-screen flex items-center justify-center bg-ink px-6">
        <div className="max-w-md text-center">
          <AlertCircle size={24} className="text-coral mx-auto mb-3" />
          <p className="text-paper text-sm mb-1.5">Can't reach the backend.</p>
          <p className="text-muted text-xs font-mono">{bootError}</p>
        </div>
      </div>
    );
  }

  if (tenants.length === 0) {
    return (
      <div className="h-screen w-screen flex items-center justify-center bg-ink px-6">
        <div className="max-w-md text-center">
          <TerminalSquare size={24} className="text-faint mx-auto mb-3" />
          <p className="text-paper text-sm mb-1.5">No tenants yet.</p>
          <p className="text-muted text-xs">
            Run <code className="font-mono text-signal">python -m app.seed</code> in the backend to load
            the two demo tenants.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen w-screen flex flex-col bg-ink overflow-hidden">
      <ConsoleHeader
        tenant={selectedTenant}
        stats={stats}
        connected={connected}
        onOpenBroadcast={() => setBroadcastOpen(true)}
      />
      <div className="flex-1 flex min-h-0">
        <TenantRail
          tenants={tenants}
          selectedId={selectedTenant?.tenant_id}
          onSelect={setSelectedTenant}
        />
        <SessionList
          sessions={sessions}
          selectedId={selectedSession?.session_id}
          onSelect={setSelectedSession}
          filter={statusFilter}
          onFilterChange={setStatusFilter}
          loading={sessionsLoading}
        />
        <ChatThread
          tenant={selectedTenant}
          session={selectedSession}
          messages={messages}
          liveEvent={liveEvent}
          onRefresh={refreshMessages}
          onNewConversation={handleNewConversation}
        />
      </div>
      <BroadcastDrawer open={broadcastOpen} onClose={() => setBroadcastOpen(false)} tenant={selectedTenant} />
    </div>
  );
}
