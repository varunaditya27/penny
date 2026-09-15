import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { AffordabilityResponse, AffordabilityStatus } from "../types";
import { colors } from "../theme/colors";
import { fontSans } from "../theme/typography";
import {
  Calendar,
  CheckCircle,
  ClockCountdown,
  Receipt,
  Sliders,
  WarningCircle,
  XCircle,
} from "./icons";

interface DecisionCardViewProps {
  decision: AffordabilityResponse;
}

const DecisionCardViewComponent: React.FC<DecisionCardViewProps> = ({ decision }) => {
  const getStatusConfig = (status: AffordabilityStatus) => {
    switch (status) {
      case "affordable_now":
        return {
          title: "AFFORDABLE NOW",
          color: colors.emerald,
          bgColor: colors.emeraldLight,
          borderColor: colors.surfaceBorderEmerald,
          Icon: CheckCircle,
        };
      case "affordable_with_plan":
        return {
          title: "AFFORDABLE WITH PLAN",
          color: colors.gold,
          bgColor: colors.goldLight,
          borderColor: colors.surfaceBorderActive,
          Icon: WarningCircle,
        };
      case "affordable_later":
        return {
          title: "AFFORDABLE LATER",
          color: colors.goldDark,
          bgColor: colors.goldLight,
          borderColor: colors.surfaceBorderActive,
          Icon: ClockCountdown,
        };
      case "not_affordable":
      default:
        return {
          title: "NOT AFFORDABLE",
          color: colors.danger,
          bgColor: colors.dangerLight,
          borderColor: "rgba(239, 68, 68, 0.35)",
          Icon: XCircle,
        };
    }
  };

  const statusConfig = getStatusConfig(decision.affordability_status);
  const StatusIcon = statusConfig.Icon;

  return (
    <View style={[styles.card, { borderColor: statusConfig.borderColor }]}>
      {/* Header Status Badge */}
      <View style={[styles.badge, { backgroundColor: statusConfig.bgColor }]}>
        <StatusIcon
          size={16}
          color={statusConfig.color}
          weight="duotone"
        />
        <Text style={[styles.badgeText, { color: statusConfig.color }]}>
          {statusConfig.title}
        </Text>
      </View>

      {/* Primary Key Figures Grid */}
      <View style={styles.metricsRow}>
        <View style={styles.metricItem}>
          <Text style={styles.metricLabel}>Safe Upfront</Text>
          <Text style={styles.metricValue}>
            ${decision.amount_safe_to_pay.toFixed(2)}
          </Text>
        </View>
        <View style={styles.metricDivider} />
        <View style={styles.metricItem}>
          <Text style={styles.metricLabel}>How to Pay</Text>
          <Text style={[styles.metricValue, { textTransform: "capitalize" }]}>
            {decision.recommended_payment_method.replace("_", " ")}
          </Text>
        </View>
        {decision.earliest_date_for_full_payment ? (
          <>
            <View style={styles.metricDivider} />
            <View style={styles.metricItem}>
              <Text style={styles.metricLabel}>Safe Date</Text>
              <View style={styles.dateRow}>
                <Calendar size={12} color={colors.textSecondary} weight="duotone" />
                <Text style={styles.metricValue}>
                  {decision.earliest_date_for_full_payment}
                </Text>
              </View>
            </View>
          </>
        ) : null}
      </View>

      {/* Payment Schedule Timeline */}
      {decision.payment_schedule && decision.payment_schedule.length > 0 ? (
        <View style={styles.scheduleSection}>
          <View style={styles.sectionHeaderRow}>
            <Receipt size={14} color={colors.textSecondary} weight="duotone" />
            <Text style={styles.sectionHeading}>PAYMENT SCHEDULE</Text>
          </View>
          <View style={styles.timelineContainer}>
            {decision.payment_schedule.map((item, idx) => (
              <View key={idx} style={styles.timelineItem}>
                <View style={styles.timelineLeft}>
                  <View
                    style={[
                      styles.timelineNode,
                      idx === 0 && { backgroundColor: statusConfig.color },
                    ]}
                  />
                  {idx < (decision.payment_schedule?.length || 0) - 1 && (
                    <View style={styles.timelineConnector} />
                  )}
                </View>
                <View style={styles.scheduleRowContent}>
                  <View>
                    <Text style={styles.scheduleIndex}>Payment {idx + 1}</Text>
                    <Text style={styles.scheduleDate}>{item.date}</Text>
                  </View>
                  <Text style={styles.scheduleAmount}>
                    ${item.amount.toFixed(2)}
                  </Text>
                </View>
              </View>
            ))}
          </View>
        </View>
      ) : null}

      {/* Required Spending Adjustments */}
      {decision.spending_changes && decision.spending_changes.length > 0 ? (
        <View style={styles.spendingSection}>
          <View style={styles.sectionHeaderRow}>
            <Sliders size={14} color={colors.gold} weight="duotone" />
            <Text style={[styles.sectionHeading, { color: colors.gold }]}>
              BUDGET CUTS NEEDED
            </Text>
          </View>
          {decision.spending_changes.map((item, idx) => (
            <View key={idx} style={styles.spendingPill}>
              <View style={styles.spendingLeft}>
                <View style={styles.spendingDot} />
                <Text style={styles.spendingAction}>
                  {item.action === "stop" ? "Pause" : "Reduce"}:
                </Text>
                <Text style={styles.spendingEvent}>{item.event_id}</Text>
              </View>
              {item.amount !== null && item.amount !== undefined ? (
                <Text style={styles.spendingAmount}>
                  to ${item.amount.toFixed(2)}
                </Text>
              ) : null}
            </View>
          ))}
        </View>
      ) : null}

      {/* Decision Reasoning Explanation */}
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
    backgroundColor: colors.surfaceCard,
    borderRadius: 16,
    padding: 18,
    borderWidth: 1.5,
    marginBottom: 16,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.35,
    shadowRadius: 10,
    elevation: 4,
  },
  badge: {
    flexDirection: "row",
    alignItems: "center",
    alignSelf: "flex-start",
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
    marginBottom: 14,
    gap: 6,
  },
  badgeText: {
    ...fontSans,
    fontSize: 11,
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
    borderWidth: 1,
    borderColor: colors.surfaceBorder,
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
    ...fontSans,
    fontSize: 10,
    fontWeight: "700",
    color: colors.textMuted,
    textTransform: "uppercase",
    letterSpacing: 0.5,
    marginBottom: 3,
  },
  metricValue: {
    ...fontSans,
    fontSize: 15,
    fontWeight: "800",
    color: colors.textPrimary,
    fontVariant: ["tabular-nums"],
  },
  dateRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
  },
  scheduleSection: {
    backgroundColor: colors.surfaceLight,
    borderRadius: 12,
    padding: 14,
    marginBottom: 14,
    borderWidth: 1,
    borderColor: colors.surfaceBorder,
  },
  sectionHeaderRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    marginBottom: 10,
  },
  sectionHeading: {
    ...fontSans,
    fontSize: 10,
    fontWeight: "800",
    letterSpacing: 0.8,
    color: colors.textSecondary,
  },
  timelineContainer: {
    marginTop: 4,
  },
  timelineItem: {
    flexDirection: "row",
    minHeight: 38,
  },
  timelineLeft: {
    width: 20,
    alignItems: "center",
  },
  timelineNode: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: colors.textDim,
    marginTop: 4,
  },
  timelineConnector: {
    width: 1.5,
    flex: 1,
    backgroundColor: colors.surfaceBorderLight,
    marginVertical: 2,
  },
  scheduleRowContent: {
    flex: 1,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
    paddingBottom: 8,
    paddingLeft: 6,
  },
  scheduleIndex: {
    ...fontSans,
    fontSize: 12,
    fontWeight: "700",
    color: colors.textPrimary,
  },
  scheduleDate: {
    ...fontSans,
    fontSize: 11,
    color: colors.textMuted,
    marginTop: 1,
  },
  scheduleAmount: {
    ...fontSans,
    fontSize: 13,
    fontWeight: "800",
    color: colors.textPrimary,
    fontVariant: ["tabular-nums"],
  },
  spendingSection: {
    marginBottom: 14,
  },
  spendingPill: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    backgroundColor: colors.goldLight,
    borderWidth: 1,
    borderColor: colors.surfaceBorderActive,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 10,
    marginTop: 6,
  },
  spendingLeft: {
    flexDirection: "row",
    alignItems: "center",
    flex: 1,
    gap: 6,
  },
  spendingDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: colors.gold,
  },
  spendingAction: {
    ...fontSans,
    fontSize: 11,
    fontWeight: "800",
    color: colors.gold,
  },
  spendingEvent: {
    ...fontSans,
    fontSize: 12,
    fontWeight: "600",
    color: colors.textPrimary,
    flex: 1,
  },
  spendingAmount: {
    ...fontSans,
    fontSize: 12,
    fontWeight: "800",
    color: colors.gold,
    fontVariant: ["tabular-nums"],
  },
  explanationSection: {
    borderTopWidth: 1,
    borderTopColor: colors.surfaceBorder,
    paddingTop: 12,
  },
  explanationText: {
    ...fontSans,
    fontSize: 13,
    lineHeight: 20,
    color: colors.textSecondary,
  },
});

export const DecisionCardView = React.memo(DecisionCardViewComponent);

