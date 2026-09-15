import React, { useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { AffordabilityResponse, ChatMessage, SSEEvent } from "../types";
import { api } from "../services/api";
import { colors } from "../theme/colors";
import { DecisionCardView } from "../components/DecisionCardView";
import { ApprovalModal } from "../components/ApprovalModal";

interface AgentChatScreenProps {
  initialQuery?: string;
}

export const AgentChatScreen: React.FC<AgentChatScreenProps> = ({
  initialQuery,
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome_msg",
      role: "assistant",
      content:
        "Hello! I am **Penny**, your agentic financial assistant.\n\nI combine 90-day forward cash flow simulation, mathematical safety invariants, and human-in-the-loop decision gating to give you honest affordability verdicts.\n\nHow can I help you today?",
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    },
  ]);
  const [inputText, setInputText] = useState<string>("");
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [agentStatus, setAgentStatus] = useState<string | null>(null);
  const [pendingApproval, setPendingApproval] = useState<any | null>(null);

  const sessionIdRef = useRef<string>(`sess_${Date.now()}`);
  const flatListRef = useRef<FlatList>(null);

  const sendMessage = async (textToSend: string) => {
    const trimmed = textToSend.trim();
    if (!trimmed || isStreaming) return;

    setInputText("");
    const userMsgId = `user_${Date.now()}`;
    const assistantMsgId = `asst_${Date.now()}`;

    const userMessage: ChatMessage = {
      id: userMsgId,
      role: "human",
      content: trimmed,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsStreaming(true);
    setAgentStatus("Supervisor analyzing query...");

    let accumulatedContent = "";
    let accumulatedDecisionCard: AffordabilityResponse | null = null;
    let accumulatedApproval: any | null = null;

    try {
      await api.sendChatStream(
        "user_01",
        trimmed,
        sessionIdRef.current,
        (event: SSEEvent) => {
          if (event.event === "status") {
            setAgentStatus(event.data?.message || "Reasoning...");
          } else if (event.event === "token") {
            const chunk =
              event.data?.content ||
              event.data?.delta ||
              event.data?.text ||
              (typeof event.data === "string" ? event.data : "");
            if (chunk) {
              accumulatedContent += chunk;
              setMessages((prev) => {
                const existingIdx = prev.findIndex((m) => m.id === assistantMsgId);
                if (existingIdx >= 0) {
                  const updated = [...prev];
                  updated[existingIdx] = {
                    ...updated[existingIdx],
                    content: accumulatedContent,
                  };
                  return updated;
                } else {
                  return [
                    ...prev,
                    {
                      id: assistantMsgId,
                      role: "assistant",
                      content: accumulatedContent,
                      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
                    },
                  ];
                }
              });
            }
          } else if (event.event === "decision_card") {
            accumulatedDecisionCard = event.data;
            setMessages((prev) => {
              const existingIdx = prev.findIndex((m) => m.id === assistantMsgId);
              if (existingIdx >= 0) {
                const updated = [...prev];
                updated[existingIdx] = {
                  ...updated[existingIdx],
                  decisionCard: accumulatedDecisionCard,
                };
                return updated;
              } else {
                return [
                  ...prev,
                  {
                    id: assistantMsgId,
                    role: "assistant",
                    content: accumulatedContent,
                    decisionCard: accumulatedDecisionCard,
                    timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
                  },
                ];
              }
            });
          } else if (
            event.event === "action_required" ||
            event.event === "approval_required"
          ) {
            accumulatedApproval =
              event.data?.interrupt?.payload || event.data;
            setPendingApproval(accumulatedApproval);
            setMessages((prev) => {
              const existingIdx = prev.findIndex((m) => m.id === assistantMsgId);
              if (existingIdx >= 0) {
                const updated = [...prev];
                updated[existingIdx] = {
                  ...updated[existingIdx],
                  pendingApproval: accumulatedApproval,
                };
                return updated;
              }
              return prev;
            });
          } else if (event.event === "done") {
            setAgentStatus(null);
            setIsStreaming(false);
          }
        }
      );
    } catch (err) {
      console.error("Chat error", err);
      setMessages((prev) => [
        ...prev,
        {
          id: `err_${Date.now()}`,
          role: "assistant",
          content: "Sorry, I encountered an error communicating with the financial reasoning graph.",
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
    } finally {
      setIsStreaming(false);
      setAgentStatus(null);
    }
  };

  useEffect(() => {
    if (initialQuery) {
      sendMessage(initialQuery);
    }
  }, [initialQuery]);

  const handleApproveAction = async () => {
    if (!pendingApproval) return;
    const approval = pendingApproval;
    setPendingApproval(null);

    try {
      const res = await api.approveChatAction(
        "user_01",
        sessionIdRef.current,
        "approve"
      );
      setMessages((prev) => [
        ...prev,
        {
          id: `appr_${Date.now()}`,
          role: "assistant",
          content: `✅ **Confirmed**: ${res.response_message || "Adjustments applied to your profile."}`,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
    } catch (err) {
      console.error("Approval error", err);
    }
  };

  const handleRejectAction = async () => {
    if (!pendingApproval) return;
    setPendingApproval(null);

    try {
      const res = await api.approveChatAction(
        "user_01",
        sessionIdRef.current,
        "reject"
      );
      setMessages((prev) => [
        ...prev,
        {
          id: `rej_${Date.now()}`,
          role: "assistant",
          content: `ℹ️ **Declined**: ${res.response_message || "No changes were applied."}`,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
    } catch (err) {
      console.error("Rejection error", err);
    }
  };

  const renderMessageItem = ({ item }: { item: ChatMessage }) => {
    const isUser = item.role === "human";
    return (
      <View
        style={[
          styles.messageRow,
          isUser ? styles.messageRowUser : styles.messageRowAsst,
        ]}
      >
        <View
          style={[
            styles.messageBubble,
            isUser ? styles.bubbleUser : styles.bubbleAsst,
          ]}
        >
          {/* Assistant Header Tag */}
          {!isUser ? (
            <View style={styles.asstTagRow}>
              <Text style={styles.asstTagText}>🪙 PENNY REASONING</Text>
              <Text style={styles.timestampText}>{item.timestamp}</Text>
            </View>
          ) : null}

          {item.content ? (
            <Text style={styles.messageContent}>{item.content}</Text>
          ) : isStreaming ? (
            <Text style={[styles.messageContent, { fontStyle: "italic", color: colors.textMuted }]}>
              {agentStatus || "Reasoning..."}
            </Text>
          ) : null}

          {/* Embedded Structured Decision Card */}
          {item.decisionCard ? (
            <View style={styles.embeddedCard}>
              <DecisionCardView decision={item.decisionCard} />
            </View>
          ) : null}

          {/* Inline Action Gate */}
          {item.pendingApproval ? (
            <View style={styles.inlineActionGate}>
              <Text style={styles.actionGateTitle}>
                ⚠️ CONFIRMATION REQUIRED
              </Text>
              <Text style={styles.actionGateDesc}>
                {item.pendingApproval.action_description}
              </Text>
              <View style={styles.actionGateButtons}>
                <TouchableOpacity
                  style={styles.gateRejectBtn}
                  onPress={handleRejectAction}
                >
                  <Text style={styles.gateRejectText}>Decline</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={styles.gateApproveBtn}
                  onPress={handleApproveAction}
                >
                  <Text style={styles.gateApproveText}>Approve</Text>
                </TouchableOpacity>
              </View>
            </View>
          ) : null}

          {isUser ? (
            <Text style={styles.userTimestamp}>{item.timestamp}</Text>
          ) : null}
        </View>
      </View>
    );
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
      keyboardVerticalOffset={80}
    >
      <FlatList
        ref={flatListRef}
        data={messages}
        renderItem={renderMessageItem}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.messagesList}
        onContentSizeChange={() =>
          flatListRef.current?.scrollToEnd({ animated: true })
        }
      />

      {/* Streaming Agent Status Bar */}
      {agentStatus ? (
        <View style={styles.agentStatusBar}>
          <ActivityIndicator size="small" color={colors.accent} />
          <Text style={styles.agentStatusText}>{agentStatus}</Text>
        </View>
      ) : null}

      {/* Suggested Prompts */}
      <View style={styles.suggestionsRow}>
        {[
          "Can I afford a $350 tablet?",
          "Show 90-day cash flow forecast",
          "How can I cut expenses to save $200?",
        ].map((prompt, i) => (
          <TouchableOpacity
            key={i}
            style={styles.suggestionChip}
            onPress={() => sendMessage(prompt)}
            disabled={isStreaming}
          >
            <Text style={styles.suggestionText}>{prompt}</Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Input Bar */}
      <View style={styles.inputBar}>
        <TextInput
          style={styles.textInput}
          value={inputText}
          onChangeText={setInputText}
          placeholder="Ask Penny about affordability, forecast, or budget..."
          placeholderTextColor={colors.textMuted}
          multiline
        />
        <TouchableOpacity
          style={[
            styles.sendButton,
            (!inputText.trim() || isStreaming) && styles.sendButtonDisabled,
          ]}
          onPress={() => sendMessage(inputText)}
          disabled={!inputText.trim() || isStreaming}
        >
          <Text style={styles.sendIcon}>➤</Text>
        </TouchableOpacity>
      </View>

      {/* Modal fallback for approval */}
      {pendingApproval ? (
        <ApprovalModal
          visible={!!pendingApproval}
          actionDescription={pendingApproval.action_description}
          proposedChanges={pendingApproval.proposed_changes || []}
          estimatedSavings={pendingApproval.estimated_monthly_savings}
          onApprove={handleApproveAction}
          onReject={handleRejectAction}
          onClose={() => setPendingApproval(null)}
        />
      ) : null}
    </KeyboardAvoidingView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  messagesList: {
    padding: 16,
    paddingBottom: 20,
  },
  messageRow: {
    marginBottom: 14,
    flexDirection: "row",
  },
  messageRowUser: {
    justifyContent: "flex-end",
  },
  messageRowAsst: {
    justifyContent: "flex-start",
  },
  messageBubble: {
    maxWidth: "88%",
    borderRadius: 16,
    padding: 14,
  },
  bubbleUser: {
    backgroundColor: colors.primaryDark,
    borderBottomRightRadius: 4,
  },
  bubbleAsst: {
    backgroundColor: colors.surface,
    borderBottomLeftRadius: 4,
    borderWidth: 1,
    borderColor: colors.surfaceBorder,
  },
  asstTagRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 8,
    borderBottomWidth: 1,
    borderBottomColor: colors.surfaceBorder,
    paddingBottom: 4,
  },
  asstTagText: {
    fontSize: 9,
    fontWeight: "800",
    color: colors.primary,
    letterSpacing: 0.8,
  },
  timestampText: {
    fontSize: 10,
    color: colors.textMuted,
  },
  userTimestamp: {
    fontSize: 10,
    color: "rgba(255, 255, 255, 0.6)",
    textAlign: "right",
    marginTop: 4,
  },
  messageContent: {
    fontSize: 14,
    lineHeight: 21,
    color: colors.textPrimary,
  },
  embeddedCard: {
    marginTop: 12,
  },
  inlineActionGate: {
    backgroundColor: colors.surfaceLight,
    borderRadius: 12,
    padding: 12,
    marginTop: 10,
    borderLeftWidth: 3,
    borderLeftColor: colors.warning,
  },
  actionGateTitle: {
    fontSize: 10,
    fontWeight: "800",
    color: colors.warning,
    letterSpacing: 0.8,
    marginBottom: 4,
  },
  actionGateDesc: {
    fontSize: 12,
    color: colors.textPrimary,
    lineHeight: 17,
    marginBottom: 10,
  },
  actionGateButtons: {
    flexDirection: "row",
    gap: 8,
  },
  gateRejectBtn: {
    flex: 1,
    backgroundColor: colors.surface,
    paddingVertical: 8,
    borderRadius: 6,
    alignItems: "center",
    borderWidth: 1,
    borderColor: colors.surfaceBorder,
  },
  gateRejectText: {
    fontSize: 11,
    fontWeight: "700",
    color: colors.textSecondary,
  },
  gateApproveBtn: {
    flex: 1,
    backgroundColor: colors.warning,
    paddingVertical: 8,
    borderRadius: 6,
    alignItems: "center",
  },
  gateApproveText: {
    fontSize: 11,
    fontWeight: "800",
    color: colors.background,
  },
  agentStatusBar: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: colors.surfaceLight,
    paddingHorizontal: 16,
    paddingVertical: 6,
    borderTopWidth: 1,
    borderTopColor: colors.surfaceBorder,
  },
  agentStatusText: {
    fontSize: 11,
    fontWeight: "600",
    color: colors.accent,
    marginLeft: 8,
  },
  suggestionsRow: {
    flexDirection: "row",
    paddingHorizontal: 12,
    paddingVertical: 6,
    backgroundColor: colors.background,
    gap: 8,
  },
  suggestionChip: {
    backgroundColor: colors.surface,
    borderRadius: 14,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderWidth: 1,
    borderColor: colors.surfaceBorder,
  },
  suggestionText: {
    fontSize: 11,
    color: colors.textSecondary,
  },
  inputBar: {
    flexDirection: "row",
    padding: 10,
    paddingHorizontal: 14,
    backgroundColor: colors.surface,
    borderTopWidth: 1,
    borderTopColor: colors.surfaceBorder,
    alignItems: "center",
  },
  textInput: {
    flex: 1,
    backgroundColor: colors.surfaceLight,
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 10,
    color: colors.textPrimary,
    fontSize: 14,
    maxHeight: 90,
  },
  sendButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: colors.primary,
    justifyContent: "center",
    alignItems: "center",
    marginLeft: 10,
  },
  sendButtonDisabled: {
    backgroundColor: colors.surfaceLight,
    opacity: 0.5,
  },
  sendIcon: {
    fontSize: 16,
    color: colors.background,
    fontWeight: "800",
  },
});
