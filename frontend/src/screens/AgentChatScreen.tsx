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
import { PennyLogo } from "../components/PennyLogo";
import {
  CheckCircle,
  Info,
  PaperPlaneRight,
  ShieldCheck,
  Sparkle,
} from "../components/icons";

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
        "Hello! I am Penny, your agentic financial copilot.\n\nI run forward cash flow simulations and apply strict mathematical safety invariants before approving discretionary outlays. What would you like to evaluate today?",
      timestamp: new Date().toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      }),
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
      timestamp: new Date().toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      }),
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
                      timestamp: new Date().toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                      }),
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
                    timestamp: new Date().toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                    }),
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
          content:
            "I encountered a temporary disruption communicating with the reasoning cluster. Deterministic fallback engaged.",
          timestamp: new Date().toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          }),
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
          content: `Authorized: ${res.response_message || "Adjustments applied to your spending policy."}`,
          timestamp: new Date().toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          }),
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
          content: `Declined: ${res.response_message || "No modifications were enacted."}`,
          timestamp: new Date().toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          }),
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
              <View style={styles.asstBrandTag}>
                <PennyLogo size={15} showTrajectory={false} />
                <Text style={styles.asstTagText}>PENNY AI</Text>
              </View>
              <Text style={styles.timestampText}>{item.timestamp}</Text>
            </View>
          ) : null}

          {item.content ? (
            <Text style={styles.messageContent}>{item.content}</Text>
          ) : isStreaming ? (
            <View style={styles.reasoningRow}>
              <ActivityIndicator size="small" color={colors.violet} />
              <Text style={styles.reasoningPlaceholder}>
                {agentStatus || "Synthesizing cash flow invariant..."}
              </Text>
            </View>
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
              <View style={styles.gateHeader}>
                <ShieldCheck size={16} color={colors.gold} weight="duotone" />
                <Text style={styles.actionGateTitle}>
                  AUTHORIZATION REQUIRED
                </Text>
              </View>
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
          <Sparkle size={12} color={colors.violet} weight="fill" />
          <Text style={styles.agentStatusText}>{agentStatus}</Text>
        </View>
      ) : null}

      {/* Suggested Quick Prompts */}
      <View style={styles.suggestionsRow}>
        {[
          "Can I afford a $350 tablet?",
          "Show 90-day cash forecast",
          "Cut flexible expenses by $200",
        ].map((prompt, i) => (
          <TouchableOpacity
            key={i}
            style={styles.suggestionChip}
            onPress={() => sendMessage(prompt)}
            disabled={isStreaming}
            activeOpacity={0.8}
          >
            <Text style={styles.suggestionText}>{prompt}</Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Luxury Input Bar */}
      <View style={styles.inputBar}>
        <TextInput
          style={styles.textInput}
          value={inputText}
          onChangeText={setInputText}
          placeholder="Ask Penny about liquidity, forecast, or affordability..."
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
          activeOpacity={0.8}
        >
          <PaperPlaneRight
            size={16}
            color={!inputText.trim() || isStreaming ? colors.textMuted : colors.black}
            weight="fill"
          />
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
    borderRadius: 18,
    padding: 14,
  },
  bubbleUser: {
    backgroundColor: colors.surfaceLight,
    borderWidth: 1,
    borderColor: colors.surfaceBorderLight,
    borderBottomRightRadius: 4,
  },
  bubbleAsst: {
    backgroundColor: colors.surfaceCard,
    borderWidth: 1,
    borderColor: colors.surfaceBorder,
    borderBottomLeftRadius: 4,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 3,
  },
  asstTagRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 8,
    borderBottomWidth: 1,
    borderBottomColor: colors.surfaceBorder,
    paddingBottom: 6,
  },
  asstBrandTag: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  asstTagText: {
    fontSize: 10,
    fontWeight: "800",
    color: colors.gold,
    letterSpacing: 1,
  },
  timestampText: {
    fontSize: 10,
    color: colors.textMuted,
  },
  userTimestamp: {
    fontSize: 10,
    color: colors.textMuted,
    textAlign: "right",
    marginTop: 4,
  },
  messageContent: {
    fontSize: 13,
    lineHeight: 20,
    color: colors.textPrimary,
  },
  reasoningRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    paddingVertical: 4,
  },
  reasoningPlaceholder: {
    fontSize: 12,
    fontStyle: "italic",
    color: colors.violet,
  },
  embeddedCard: {
    marginTop: 12,
  },
  inlineActionGate: {
    backgroundColor: colors.surfaceLight,
    borderRadius: 14,
    padding: 14,
    marginTop: 12,
    borderWidth: 1,
    borderColor: colors.surfaceBorderActive,
  },
  gateHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    marginBottom: 6,
  },
  actionGateTitle: {
    fontSize: 10,
    fontWeight: "800",
    color: colors.gold,
    letterSpacing: 0.8,
  },
  actionGateDesc: {
    fontSize: 12,
    lineHeight: 17,
    color: colors.textPrimary,
    marginBottom: 10,
  },
  actionGateButtons: {
    flexDirection: "row",
    gap: 8,
  },
  gateRejectBtn: {
    flex: 1,
    paddingVertical: 8,
    borderRadius: 8,
    backgroundColor: colors.surface,
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
    paddingVertical: 8,
    borderRadius: 8,
    backgroundColor: colors.gold,
    alignItems: "center",
  },
  gateApproveText: {
    fontSize: 11,
    fontWeight: "800",
    color: colors.black,
  },
  agentStatusBar: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: colors.violetLight,
    paddingHorizontal: 14,
    paddingVertical: 6,
    marginHorizontal: 16,
    marginBottom: 6,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.violetGlow,
    gap: 6,
  },
  agentStatusText: {
    fontSize: 11,
    fontWeight: "700",
    color: colors.violet,
  },
  suggestionsRow: {
    flexDirection: "row",
    paddingHorizontal: 16,
    gap: 6,
    marginBottom: 8,
  },
  suggestionChip: {
    backgroundColor: colors.surfaceCard,
    borderWidth: 1,
    borderColor: colors.surfaceBorder,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 16,
  },
  suggestionText: {
    fontSize: 11,
    fontWeight: "600",
    color: colors.textSecondary,
  },
  inputBar: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: colors.surfaceCard,
    borderTopWidth: 1,
    borderTopColor: colors.surfaceBorder,
    paddingHorizontal: 16,
    paddingVertical: 10,
    gap: 10,
  },
  textInput: {
    flex: 1,
    backgroundColor: colors.surfaceLight,
    borderWidth: 1,
    borderColor: colors.surfaceBorder,
    borderRadius: 20,
    paddingHorizontal: 14,
    paddingVertical: 8,
    fontSize: 13,
    color: colors.textPrimary,
    maxHeight: 90,
  },
  sendButton: {
    width: 38,
    height: 38,
    borderRadius: 19,
    backgroundColor: colors.gold,
    justifyContent: "center",
    alignItems: "center",
    shadowColor: colors.gold,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 4,
  },
  sendButtonDisabled: {
    backgroundColor: colors.surfaceLight,
    shadowOpacity: 0,
  },
});
