import { createContext, useContext, useState, useCallback, useMemo, useRef, useEffect } from "react";
import { api } from "../lib/api";

const ZoeyContext = createContext(null);

const TERMINAL_STATUSES = new Set([
  "completed",
  "failed",
  "cancelled",
  "blocked",
  "no_executable_steps",
]);

function makeId(prefix) {
  return `${prefix}${Date.now()}${Math.floor(Math.random() * 1000)}`;
}

function summaryForStatus(status, steps) {
  const done = steps.filter((s) => s.status === "completed").length;
  const failed = steps.filter((s) => s.status === "failed").length;

  if (status === "cancelled") {
    return `Plan stopped${done ? ` — ${done} step${done === 1 ? "" : "s"} done.` : "."}`;
  }
  if (status === "failed") {
    return `Plan failed — ${failed} step${failed === 1 ? "" : "s"} failed, ${done} done.`;
  }
  if (status === "blocked") {
    return `Plan blocked — some steps couldn't run.`;
  }
  if (status === "no_executable_steps") {
    return `Plan saved, but none of the steps are auto-executable.`;
  }
  return `Plan completed — ${done} step${done === 1 ? "" : "s"} done.`;
}

function pushMessage(setMessages, msg) {
  setMessages((m) => [...m, msg]);
}

export function ZoeyProvider({ children }) {
  const [panel, setPanel] = useState({ view: null });
  const [assistantState, setAssistantState] = useState("idle");
  const [messages, setMessages] = useState([]);
  const [decision, setDecision] = useState(null);
  const [plan, setPlan] = useState(null);
  const [execution, setExecution] = useState(null);

  const pollRef = useRef(null);
  const terminalRef = useRef(false);
  const inFlightRef = useRef(false);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  useEffect(() => () => stopPolling(), [stopPolling]);

  const sendMessage = useCallback(async (text) => {
    if (!text.trim()) return;
    if (inFlightRef.current) return;

    inFlightRef.current = true;
    terminalRef.current = false;

    setMessages((m) => [...m, { id: makeId("u"), role: "user", type: "text", content: text }]);
    setAssistantState("thinking");

    try {
      const { data } = await api.chat(text);
      const msg = data.message;

      if (msg.type === "plan_pending") {
        setPlan(msg.data.plan);
        setDecision(null);
      } else if (msg.type === "goal") {
        setPlan(msg.data.plan);
        setDecision("approved");
      } else if (msg.type === "goal_rejected") {
        setDecision("rejected");
      } else if (msg.type === "plan_executed") {
        setExecution({
          goal: msg.data.goal,
          steps: msg.data.steps || [],
          status: msg.data.status || "completed",
        });
        setAssistantState(msg.data.status === "failed" ? "failed" : "idle");
      } else if (msg.type === "execution_status") {
        if (msg.data.status === "idle") {
          setExecution(null);
        } else if (msg.data.steps && msg.data.steps.length) {
          setExecution({
            goal: msg.data.goal,
            steps: msg.data.steps,
            status: msg.data.status,
          });
        }
      }

      setMessages((m) => [...m, msg]);
      if (msg.type !== "plan_executed") setAssistantState("idle");
    } catch (err) {
      pushMessage(setMessages, {
        id: makeId("e"),
        role: "assistant",
        type: "error",
        content: err.message || "Request failed.",
      });
      setAssistantState("failed");
    } finally {
      inFlightRef.current = false;
    }
  }, []);

  const approvePlan = useCallback(async () => {
    try {
      const { data } = await api.approvePlan();
      setDecision("approved");
      if (data.plan) setPlan(data.plan);

      const tasks = data.tasks || [];
      const note =
        tasks.length > 0
          ? `Approved — ${tasks.length} task${tasks.length === 1 ? "" : "s"} saved. Say "execute the plan" or press Execute to run it.`
          : "Plan approved. Say \"execute the plan\" or press Execute to run it.";
      pushMessage(setMessages, {
        id: makeId("a"),
        role: "assistant",
        type: "text",
        content: note,
      });
    } catch (err) {
      pushMessage(setMessages, {
        id: makeId("e"),
        role: "assistant",
        type: "error",
        content: err.message || "Approval failed.",
      });
      setAssistantState("failed");
    }
  }, []);

  const rejectPlan = useCallback(async () => {
    try {
      await api.rejectPlan();
      setDecision("rejected");
      pushMessage(setMessages, {
        id: makeId("r"),
        role: "assistant",
        type: "text",
        content: "Plan discarded.",
      });
    } catch (err) {
      pushMessage(setMessages, {
        id: makeId("e"),
        role: "assistant",
        type: "error",
        content: err.message || "Couldn't discard the plan.",
      });
      setAssistantState("failed");
    }
  }, []);

  const executePlan = useCallback(async () => {
    if (!plan) return;

    try {
      await api.executePlan();
      terminalRef.current = false;
      setExecution({ goal: plan.goal, steps: [], status: "running" });
      setAssistantState("executing");
    } catch (err) {
      // e.g. "There's no approved plan to execute." — surfaced as an
      // error rather than fabricating or bypassing approval state.
      pushMessage(setMessages, {
        id: makeId("e"),
        role: "assistant",
        type: "error",
        content: err.message || "Couldn't start execution.",
      });
      setAssistantState("idle");
    }
  }, [plan]);

  const cancelExecution = useCallback(async () => {
    try {
      await api.cancelExecution();
    } catch (err) {
      pushMessage(setMessages, {
        id: makeId("e"),
        role: "assistant",
        type: "error",
        content: err.message || "Couldn't stop execution.",
      });
    }
  }, []);

  // Poll /api/status while execution is running so steps stream live.
  useEffect(() => {
    if (assistantState !== "executing") return;

    stopPolling();
    terminalRef.current = false;

    const tick = async () => {
      try {
        const { data } = await api.status();
        const status = data.status || "idle";

        setExecution((prev) =>
          prev ? { ...prev, steps: data.steps || prev.steps, status } : prev
        );

        if (TERMINAL_STATUSES.has(status) && !terminalRef.current) {
          terminalRef.current = true;
          stopPolling();

          const finalSteps = data.steps || [];
          setExecution((prev) =>
            prev ? { ...prev, steps: finalSteps, status } : prev
          );

          pushMessage(setMessages, {
            id: makeId("x"),
            role: "assistant",
            type: "text",
            content: summaryForStatus(status, finalSteps),
          });

          setAssistantState(status === "failed" ? "failed" : status === "completed" ? "completed" : "idle");
        }
      } catch {
        // Transient poll error: keep polling; the next tick retries.
      }
    };

    pollRef.current = setInterval(tick, 400);
    tick();

    return stopPolling;
  }, [assistantState, stopPolling]);

  const openPanel = useCallback((view) => {
    setPanel((p) => ({ view: p.view === view ? null : view }));
  }, []);

  const newConversation = useCallback(() => {
    terminalRef.current = false;
    stopPolling();
    setMessages([]);
    setDecision(null);
    setPlan(null);
    setExecution(null);
    setAssistantState("idle");
  }, [stopPolling]);

  const conversations = useMemo(() => {
    const first = messages.find((m) => m.role === "user");
    return [
      {
        id: "current",
        title: first ? first.content : "New conversation",
        updated: "now",
        active: true,
      },
    ];
  }, [messages]);

  const value = {
    conversations,
    panel,
    openPanel,
    newConversation,
    assistantState,
    setAssistantState,
    plan,
    decision,
    approvePlan,
    rejectPlan,
    executePlan,
    steps: execution ? execution.steps : [],
    execStatus: execution ? execution.status : "idle",
    execution,
    cancelExecution,
    messages,
    sendMessage,
  };

  return <ZoeyContext.Provider value={value}>{children}</ZoeyContext.Provider>;
}

export function useZoey() {
  const ctx = useContext(ZoeyContext);
  if (!ctx) throw new Error("useZoey must be used within ZoeyProvider");
  return ctx;
}
