import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { AffordabilityResponse, AffordabilityStatus } from "../types";
import { colors } from "../theme/colors";

interface DecisionCardViewProps {
  decision: AffordabilityResponse;
}

export const DecisionCardView: React.FC<DecisionCardViewProps> = ({ decision }) => {
  const getStatusConfig = (status: AffordabilityStatus) => {
    switch (status) {
      case "affordable_now":
        return {
          title: "AFFORDABLE NOW",
          color: colors.success,
          bgColor: colors.successLight,
          icon: "✅",
        };
      case "affordable_with_plan":
        return {
          title: "AFFORDABLE WITH PLAN",
          color: colors.warning,
          bgColor: colors.warningLight,
          icon: "⚠️",
        };
      case "affordable_later":
        return {
          title: "AFFORDABLE LATER",
          color: colors.accent,
          bgColor: colors.accentLight,
          icon: "⏳",
        };
      case "not_affordable":
      default:
        return {
          title: "NOT AFFORDABLE",
          color: colors.danger,
          bgColor: colors.dangerLight,
          icon: "🛑",
        };
    }
  };

  const statusConfig = getStatusConfig(decision.affordability_status);

  return (
    <View style={[styles.card, { borderColor: statusConfig.color }]}>
      {/* Header Status Badge */}
      <View style={[styles.badge, { backgroundColor: statusConfig.bgColor }]}>
        <Text style={styles.badgeIcon}>{statusConfig.icon}</Text>
        <Text style={[styles.badgeText, { color: statusConfig.color }]}>
          {statusConfig.title}
        </Text>
      </View>

      {/* Primary Key Figures */}
      <View style={styles.metricsRow}>
        <View style={styles.metricItem}>
          <Text style={styles.metricLabel}>Safe Spend</Text>
          <Text style={styles.metricValue}>
            ${decision.amount_safe_to_pay.toFixed(2)}
          </Text>
        </View>
        <View style={styles.metricDivider} />
        <View style={styles.metricItem}>
          <Text style={styles.metricLabel}>Structure</Text>
          <Text style={[styles.metricValue, { textTransform: "capitalize" }]}>
            {decision.recommended_payment_method.replace("_", " ")}
          </Text>
        </View>
        {decision.earliest_date_for_full_payment ? (
          <>
            <View style={styles.metricDivider} />
            <View style={styles.metricItem}>
              <Text style={styles.metricLabel}>Earliest Date</Text>
              <Text style={styles.metricValue}>
                {decision.earliest_date_for_full_payment}
              </Text>
            </View>
          </>
        ) : null}
      </View>

      {/* Payment Schedule Table if installments */}
      {decision.payment_schedule && decision.payment_schedule.length > 0 ? (
        <View style={styles.scheduleSection}>
          <Text style={styles.sectionHeading}>RECOMMENDED PAYMENT SCHEDULE</Text>
          {decision.payment_schedule.map((item, idx) => (
            <View key={idx} style={styles.scheduleRow}>
              <Text style={styles.scheduleIndex}>Payment {idx + 1}</Text>
              <Text style={styles.scheduleDate}>{item.date}</Text>
              <Text style={styles.scheduleAmount}>${item.amount.toFixed(2)}</Text>
            </View>
          ))}
        </View>
      ) : null}

      {/* Spending Changes Needed */}
      {decision.spending_changes && decision.spending_changes.length > 0 ? (
        <View style={styles.spendingSection}>
          <Text style={styles.sectionHeading}>REQUIRED SPENDING ADJUSTMENTS</Text>
          {decision.spending_changes.map((item, idx) => (
            <View key={idx} style={styles.spendingPill}>
              <Text style={styles.spendingAction}>
                {item.action === "stop" ? "Pause" : "Reduce"}:
              </Text>
              <Text style={styles.spendingEvent}>{item.event_id}</Text>
              {item.amount ? (
                <Text style={styles.spendingAmount}>
                  to ${item.amount.toFixed(2)}
                </Text>
              ) : null}
            </View>
          ))}
        </View>
      ) : null}

      {/* Decision Explanation */}
      <View style={styles.explanationSection}>
        <Text style={styles.explanationText}>
          {decision.decision_explanation}
        </Text>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.surface,
    borderRadius: 16,
    padding: 18,
    borderWidth: 1.5,
    marginBottom: 16,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.3,
    shadowRadius: 5,
    elevation: 3,
  },
  badge: {
    flexDirection: "row",
    alignItems: "center",
    alignSelf: "flex-start",
    paddingHorizontal: 12,
    paddingVertical: 5,
    borderRadius: 20,
    marginBottom: 14,
  },
  badgeIcon: {
    fontSize: 12,
    marginRight: 6,
  },
  badgeText: {
    fontSize: 12,
    fontWeight: "800",
    letterSpacing: 0.8,
  },
  metricsRow: {
    flexDirection: "row",
    backgroundColor: colors.surfaceLight,
    borderRadius: 12,
    padding: 12,
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 14,
  },
  metricItem: {
    flex: 1,
    alignItems: "center",
  },
  metricDivider: {
    width: 1,
    height: 24,
    backgroundColor: colors.surfaceBorder,
  },
  metricLabel: {
    fontSize: 10,
    fontWeight: "600",
    color: colors.textMuted,
    textTransform: "uppercase",
    marginBottom: 3,
  },
  metricValue: {
    fontSize: 15,
    fontWeight: "700",
    color: colors.textPrimary,
  },
  scheduleSection: {
    backgroundColor: colors.surfaceLight,
    borderRadius: 12,
    padding: 12,
    marginBottom: 14,
  },
  sectionHeading: {
    fontSize: 10,
    fontWeight: "700",
    letterSpacing: 0.8,
    color: colors.textSecondary,
    marginBottom: 8,
  },
  scheduleRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingVertical: 5,
    borderBottomWidth: 1,
    borderBottomColor: colors.surfaceBorder,
  },
  scheduleIndex: {
    fontSize: 12,
    fontWeight: "600",
    color: colors.textSecondary,
  },
  scheduleDate: {
    fontSize: 12,
    color: colors.textMuted,
  },
  scheduleAmount: {
    fontSize: 12,
    fontWeight: "700",
    color: colors.textPrimary,
  },
  spendingSection: {
    marginBottom: 14,
  },
  spendingPill: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "rgba(245, 158, 11, 0.12)",
    borderWidth: 1,
    borderColor: "rgba(245, 158, 11, 0.3)",
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 8,
    marginTop: 4,
  },
  spendingAction: {
    fontSize: 11,
    fontWeight: "700",
    color: colors.warning,
    marginRight: 6,
  },
  spendingEvent: {
    fontSize: 11,
    fontWeight: "600",
    color: colors.textPrimary,
    flex: 1,
  },
  spendingAmount: {
    fontSize: 11,
    fontWeight: "700",
    color: colors.warning,
  },
  explanationSection: {
    borderTopWidth: 1,
    borderTopColor: colors.surfaceBorder,
    paddingTop: 10,
  },
  explanationText: {
    fontSize: 13,
    lineHeight: 19,
    color: colors.textSecondary,
  },
});
