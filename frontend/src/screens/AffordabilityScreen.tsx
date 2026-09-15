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
import {
  Calendar,
  ChatCircle,
  CreditCard,
  Receipt,
  Sparkle,
  TrendUp,
} from "../components/icons";

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
  const [description, setDescription] = useState<string>(
    "Bose Noise Cancelling Headphones"
  );
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

  const quickPresets = [250, 750, 1500, 3000];

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* Input Form Glass Studio */}
      <View style={styles.formCard}>
        <View style={styles.formHeaderRow}>
          <CreditCard size={16} color={colors.gold} weight="duotone" />
          <Text style={styles.formTitle}>PURCHASE AFFORDABILITY SIMULATOR</Text>
        </View>

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

        {/* Tactile Quick Amount Chips */}
        <View style={styles.chipRow}>
          {quickPresets.map((preset) => (
            <TouchableOpacity
              key={preset}
              style={[
                styles.chip,
                amount === preset.toString() && styles.chipActive,
              ]}
              onPress={() => setAmount(preset.toString())}
              activeOpacity={0.8}
            >
              <Text
                style={[
                  styles.chipText,
                  amount === preset.toString() && styles.chipTextActive,
                ]}
              >
                ${preset.toLocaleString()}
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* Target Completion Date */}
        <Text style={[styles.fieldLabel, { marginTop: 14 }]}>
          TARGET COMPLETION DATE
        </Text>
        <View style={styles.dateInputContainer}>
          <Calendar size={16} color={colors.textMuted} weight="duotone" />
          <TextInput
            style={styles.dateInput}
            value={targetDate}
            onChangeText={setTargetDate}
            placeholder="YYYY-MM-DD"
            placeholderTextColor={colors.textMuted}
          />
        </View>

        {/* Allow Partial / Installments Toggle */}
        <View style={styles.toggleRow}>
          <View style={styles.toggleTextContainer}>
            <View style={styles.toggleTitleRow}>
              <Receipt size={14} color={colors.sky} weight="duotone" />
              <Text style={styles.toggleLabel}>Allow Installment Plans</Text>
            </View>
            <Text style={styles.toggleSubtext}>
              Optimize split payments if upfront charge breaches minimum reserve
            </Text>
          </View>
          <Switch
            value={allowsPartial}
            onValueChange={setAllowsPartial}
            trackColor={{ false: colors.surfaceLight, true: colors.gold }}
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
            <ActivityIndicator size="small" color={colors.black} />
          ) : (
            <View style={styles.btnContentRow}>
              <Sparkle size={16} color={colors.black} weight="fill" />
              <Text style={styles.evaluateButtonText}>
                Simulate Affordability Invariant
              </Text>
            </View>
          )}
        </TouchableOpacity>
      </View>

      {/* Decision Output Card */}
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
                  `Penny, evaluate why buying ${description} for $${amount} is ${decision.affordability_status}.`
                )
              }
              activeOpacity={0.8}
            >
              <ChatCircle size={16} color={colors.violet} weight="duotone" />
              <Text style={styles.chatActionBtnText}>
                Discuss with Penny AI
              </Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={styles.trajActionBtn}
              onPress={onNavigateToTrajectory}
              activeOpacity={0.8}
            >
              <TrendUp size={16} color={colors.sky} weight="duotone" />
              <Text style={styles.trajActionBtnText}>
                View Trajectory Dip
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
    backgroundColor: colors.surfaceCard,
    borderRadius: 20,
    padding: 20,
    borderWidth: 1.5,
    borderColor: colors.surfaceBorder,
    marginBottom: 16,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.35,
    shadowRadius: 10,
    elevation: 4,
  },
  formHeaderRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    marginBottom: 14,
  },
  formTitle: {
    fontSize: 11,
    fontWeight: "800",
    color: colors.gold,
    letterSpacing: 0.8,
  },
  fieldLabel: {
    fontSize: 10,
    fontWeight: "800",
    color: colors.textMuted,
    letterSpacing: 0.8,
    marginBottom: 6,
  },
  textInput: {
    backgroundColor: colors.surfaceLight,
    borderWidth: 1,
    borderColor: colors.surfaceBorder,
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 14,
    color: colors.textPrimary,
  },
  amountInputRow: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: colors.surfaceLight,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.surfaceBorder,
    paddingHorizontal: 14,
  },
  currencyPrefix: {
    fontSize: 22,
    fontWeight: "800",
    color: colors.gold,
    marginRight: 6,
  },
  amountInput: {
    flex: 1,
    fontSize: 22,
    fontWeight: "800",
    color: colors.textPrimary,
    paddingVertical: 10,
    fontVariant: ["tabular-nums"],
  },
  chipRow: {
    flexDirection: "row",
    gap: 8,
    marginTop: 10,
  },
  chip: {
    flex: 1,
    paddingVertical: 8,
    backgroundColor: colors.surfaceLight,
    borderRadius: 10,
    alignItems: "center",
    borderWidth: 1,
    borderColor: colors.surfaceBorder,
  },
  chipActive: {
    backgroundColor: colors.goldLight,
    borderColor: colors.surfaceBorderActive,
  },
  chipText: {
    fontSize: 12,
    fontWeight: "700",
    color: colors.textSecondary,
    fontVariant: ["tabular-nums"],
  },
  chipTextActive: {
    color: colors.gold,
  },
  dateInputContainer: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: colors.surfaceLight,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.surfaceBorder,
    paddingHorizontal: 14,
    gap: 8,
  },
  dateInput: {
    flex: 1,
    fontSize: 14,
    color: colors.textPrimary,
    paddingVertical: 12,
  },
  toggleRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginVertical: 16,
    paddingVertical: 12,
    borderTopWidth: 1,
    borderBottomWidth: 1,
    borderColor: colors.surfaceBorder,
  },
  toggleTextContainer: {
    flex: 1,
    paddingRight: 12,
  },
  toggleTitleRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  toggleLabel: {
    fontSize: 13,
    fontWeight: "700",
    color: colors.textPrimary,
  },
  toggleSubtext: {
    fontSize: 11,
    color: colors.textMuted,
    marginTop: 3,
    lineHeight: 15,
  },
  evaluateButton: {
    backgroundColor: colors.gold,
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: "center",
    justifyContent: "center",
    shadowColor: colors.gold,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.35,
    shadowRadius: 8,
    elevation: 4,
  },
  btnContentRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  evaluateButtonText: {
    fontSize: 13,
    fontWeight: "900",
    color: colors.black,
    letterSpacing: 0.4,
  },
  resultSection: {
    marginTop: 8,
  },
  resultHeading: {
    fontSize: 11,
    fontWeight: "800",
    letterSpacing: 1,
    color: colors.textSecondary,
    marginBottom: 10,
  },
  actionRow: {
    flexDirection: "row",
    gap: 10,
    marginTop: 4,
  },
  chatActionBtn: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.violetLight,
    borderWidth: 1,
    borderColor: colors.violetGlow,
    paddingVertical: 12,
    borderRadius: 12,
    gap: 6,
  },
  chatActionBtnText: {
    fontSize: 12,
    fontWeight: "700",
    color: colors.violet,
  },
  trajActionBtn: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.skyLight,
    borderWidth: 1,
    borderColor: colors.skyGlow,
    paddingVertical: 12,
    borderRadius: 12,
    gap: 6,
  },
  trajActionBtnText: {
    fontSize: 12,
    fontWeight: "700",
    color: colors.sky,
  },
});
