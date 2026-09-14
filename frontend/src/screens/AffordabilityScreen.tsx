import React, { useState } from "react";
import {
  ActivityIndicator,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { AffordabilityResponse } from "../types";
import { api } from "../services/api";
import { colors } from "../theme/colors";
import { DecisionCardView } from "../components/DecisionCardView";

interface AffordabilityScreenProps {
  onNavigateToChat: (initialQuery?: string) => void;
  onNavigateToTrajectory: () => void;
}

export const AffordabilityScreen: React.FC<AffordabilityScreenProps> = ({
  onNavigateToChat,
  onNavigateToTrajectory,
}) => {
  const [amount, setAmount] = useState<string>("250");
  const [targetDate, setTargetDate] = useState<string>("2026-03-31");
  const [allowsPartial, setAllowsPartial] = useState<boolean>(true);
  const [description, setDescription] = useState<string>("Bose Noise Cancelling Headphones");
  const [loading, setLoading] = useState<boolean>(false);
  const [decision, setDecision] = useState<AffordabilityResponse | null>(null);

  const handleEvaluate = async () => {
    const numAmt = parseFloat(amount);
    if (!numAmt || numAmt <= 0) return;

    setLoading(true);
    try {
      const res = await api.evaluateAffordability({
        user_id: "user_01",
        requested_amount: numAmt,
        desired_completion_date: targetDate,
        allows_partial_payment: allowsPartial,
        request_text: description,
      });
      setDecision(res);
    } catch (err) {
      console.error("Evaluation error", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* Input Form Card */}
      <View style={styles.formCard}>
        <Text style={styles.formTitle}>PURCHASE AFFORDABILITY SIMULATOR</Text>

        {/* Item Description */}
        <Text style={styles.fieldLabel}>ITEM OR EXPENSE DESCRIPTION</Text>
        <TextInput
          style={styles.textInput}
          value={description}
          onChangeText={setDescription}
          placeholder="e.g. Noise cancelling headphones"
          placeholderTextColor={colors.textMuted}
        />

        {/* Amount Input */}
        <Text style={[styles.fieldLabel, { marginTop: 14 }]}>REQUESTED AMOUNT</Text>
        <View style={styles.amountInputRow}>
          <Text style={styles.currencyPrefix}>$</Text>
          <TextInput
            style={styles.amountInput}
            value={amount}
            onChangeText={setAmount}
            keyboardType="numeric"
            placeholder="0.00"
            placeholderTextColor={colors.textMuted}
          />
        </View>

        {/* Preset Chips */}
        <View style={styles.chipRow}>
          {[75, 250, 600, 1200].map((preset) => (
            <TouchableOpacity
              key={preset}
              style={[
                styles.chip,
                amount === preset.toString() && styles.chipActive,
              ]}
              onPress={() => setAmount(preset.toString())}
            >
              <Text
                style={[
                  styles.chipText,
                  amount === preset.toString() && styles.chipTextActive,
                ]}
              >
                ${preset}
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* Target Completion Date */}
        <Text style={[styles.fieldLabel, { marginTop: 14 }]}>
          TARGET COMPLETION DATE (YYYY-MM-DD)
        </Text>
        <TextInput
          style={styles.textInput}
          value={targetDate}
          onChangeText={setTargetDate}
          placeholder="2026-03-31"
          placeholderTextColor={colors.textMuted}
        />

        {/* Allow Partial / Installments Toggle */}
        <View style={styles.toggleRow}>
          <View style={styles.toggleTextContainer}>
            <Text style={styles.toggleLabel}>Allow Installment Plans</Text>
            <Text style={styles.toggleSubtext}>
              Evaluate split payments if full upfront payment breaches reserve
            </Text>
          </View>
          <Switch
            value={allowsPartial}
            onValueChange={setAllowsPartial}
            trackColor={{ false: colors.surfaceBorder, true: colors.primary }}
            thumbColor={colors.white}
          />
        </View>

        {/* Action Button */}
        <TouchableOpacity
          style={styles.evaluateButton}
          onPress={handleEvaluate}
          activeOpacity={0.8}
          disabled={loading}
        >
          {loading ? (
            <ActivityIndicator size="small" color={colors.background} />
          ) : (
            <Text style={styles.evaluateButtonText}>
              Evaluate Affordability Invariant
            </Text>
          )}
        </TouchableOpacity>
      </View>

      {/* Decision Card Output */}
      {decision ? (
        <View style={styles.resultSection}>
          <Text style={styles.resultHeading}>AFFORDABILITY VERDICT</Text>
          <DecisionCardView decision={decision} />

          {/* Action Row */}
          <View style={styles.actionRow}>
            <TouchableOpacity
              style={styles.chatActionBtn}
              onPress={() =>
                onNavigateToChat(
                  `Penny, explain why buying ${description} for $${amount} is ${decision.affordability_status}.`
                )
              }
              activeOpacity={0.8}
            >
              <Text style={styles.chatActionBtnText}>
                🤖 Discuss Strategy with Penny
              </Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={styles.trajActionBtn}
              onPress={onNavigateToTrajectory}
              activeOpacity={0.8}
            >
              <Text style={styles.trajActionBtnText}>
                📈 View Trajectory Dip
              </Text>
            </TouchableOpacity>
          </View>
        </View>
      ) : null}
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  content: {
    padding: 16,
    paddingBottom: 40,
  },
  formCard: {
    backgroundColor: colors.surface,
    borderRadius: 18,
    padding: 18,
    borderWidth: 1,
    borderColor: colors.surfaceBorder,
    marginBottom: 16,
  },
  formTitle: {
    fontSize: 11,
    fontWeight: "800",
    color: colors.textSecondary,
    letterSpacing: 0.8,
    marginBottom: 14,
  },
  fieldLabel: {
    fontSize: 10,
    fontWeight: "700",
    color: colors.textMuted,
    letterSpacing: 0.5,
    marginBottom: 6,
  },
  textInput: {
    backgroundColor: colors.surfaceLight,
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 10,
    color: colors.textPrimary,
    fontSize: 14,
    fontWeight: "600",
    borderWidth: 1,
    borderColor: colors.surfaceBorder,
  },
  amountInputRow: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: colors.surfaceLight,
    borderRadius: 10,
    paddingHorizontal: 14,
    borderWidth: 1,
    borderColor: colors.surfaceBorder,
  },
  currencyPrefix: {
    fontSize: 22,
    fontWeight: "800",
    color: colors.textSecondary,
    marginRight: 6,
  },
  amountInput: {
    flex: 1,
    fontSize: 24,
    fontWeight: "800",
    color: colors.textPrimary,
    paddingVertical: 8,
  },
  chipRow: {
    flexDirection: "row",
    gap: 8,
    marginTop: 10,
  },
  chip: {
    paddingHorizontal: 14,
    paddingVertical: 6,
    borderRadius: 8,
    backgroundColor: colors.surfaceLight,
    borderWidth: 1,
    borderColor: colors.surfaceBorder,
  },
  chipActive: {
    borderColor: colors.primary,
    backgroundColor: "rgba(56, 189, 248, 0.15)",
  },
  chipText: {
    fontSize: 12,
    fontWeight: "700",
    color: colors.textSecondary,
  },
  chipTextActive: {
    color: colors.primary,
  },
  toggleRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginTop: 16,
    paddingVertical: 8,
    borderTopWidth: 1,
    borderTopColor: colors.surfaceBorder,
  },
  toggleTextContainer: {
    flex: 1,
    marginRight: 10,
  },
  toggleLabel: {
    fontSize: 13,
    fontWeight: "700",
    color: colors.textPrimary,
  },
  toggleSubtext: {
    fontSize: 11,
    color: colors.textMuted,
    marginTop: 2,
  },
  evaluateButton: {
    backgroundColor: colors.primary,
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: "center",
    marginTop: 18,
    shadowColor: colors.primary,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 4,
  },
  evaluateButtonText: {
    fontSize: 14,
    fontWeight: "800",
    color: colors.background,
    letterSpacing: 0.5,
  },
  resultSection: {
    marginTop: 8,
  },
  resultHeading: {
    fontSize: 11,
    fontWeight: "800",
    color: colors.textSecondary,
    letterSpacing: 0.8,
    marginBottom: 10,
  },
  actionRow: {
    flexDirection: "row",
    gap: 10,
    marginTop: 6,
  },
  chatActionBtn: {
    flex: 1,
    backgroundColor: colors.surface,
    paddingVertical: 12,
    borderRadius: 10,
    alignItems: "center",
    borderWidth: 1,
    borderColor: colors.accent,
  },
  chatActionBtnText: {
    fontSize: 12,
    fontWeight: "700",
    color: colors.accent,
  },
  trajActionBtn: {
    flex: 1,
    backgroundColor: colors.surface,
    paddingVertical: 12,
    borderRadius: 10,
    alignItems: "center",
    borderWidth: 1,
    borderColor: colors.surfaceBorder,
  },
  trajActionBtnText: {
    fontSize: 12,
    fontWeight: "700",
    color: colors.textSecondary,
  },
});
