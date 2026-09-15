import React from "react";
import { Modal, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { colors } from "../theme/colors";
import { CheckCircle, ShieldCheck, TrendUp, XCircle } from "./icons";

interface ApprovalModalProps {
  visible: boolean;
  actionDescription: string;
  proposedChanges: string[];
  estimatedSavings?: number;
  onApprove: () => void;
  onReject: () => void;
  onClose: () => void;
}

export const ApprovalModal: React.FC<ApprovalModalProps> = ({
  visible,
  actionDescription,
  proposedChanges,
  estimatedSavings,
  onApprove,
  onReject,
  onClose,
}) => {
  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      onRequestClose={onClose}
    >
      <View style={styles.overlay}>
        <View style={styles.card}>
          <View style={styles.headerRow}>
            <View style={styles.iconCircle}>
              <ShieldCheck size={24} color={colors.gold} weight="duotone" />
            </View>
            <View style={styles.headerTitles}>
              <View style={styles.badgeRow}>
                <View style={styles.liveDot} />
                <Text style={styles.badgeText}>HUMAN-IN-THE-LOOP GATE</Text>
              </View>
              <Text style={styles.title}>Confirm Financial Mutation</Text>
            </View>
            <TouchableOpacity
              onPress={onClose}
              hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
              style={styles.closeBtn}
            >
              <XCircle size={20} color={colors.textMuted} weight="regular" />
            </TouchableOpacity>
          </View>

          <Text style={styles.description}>{actionDescription}</Text>

          {estimatedSavings ? (
            <View style={styles.savingsBox}>
              <View style={styles.savingsHeader}>
                <TrendUp size={14} color={colors.emerald} weight="bold" />
                <Text style={styles.savingsLabel}>UNLOCKED MONTHLY HEADROOM</Text>
              </View>
              <Text style={styles.savingsValue}>
                +${estimatedSavings.toFixed(2)}/mo
              </Text>
            </View>
          ) : null}

          <View style={styles.changesSection}>
            <Text style={styles.sectionHeading}>PROPOSED ADJUSTMENTS</Text>
            {proposedChanges.map((change, idx) => (
              <View key={idx} style={styles.changeRow}>
                <CheckCircle size={14} color={colors.emerald} weight="duotone" />
                <Text style={styles.changeText}>{change}</Text>
              </View>
            ))}
          </View>

          <View style={styles.actionsRow}>
            <TouchableOpacity
              style={[styles.button, styles.rejectButton]}
              onPress={onReject}
              activeOpacity={0.8}
            >
              <Text style={styles.rejectText}>Decline</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.button, styles.approveButton]}
              onPress={onApprove}
              activeOpacity={0.8}
            >
              <Text style={styles.approveText}>Authorize Changes</Text>
            </TouchableOpacity>
          </View>
        </View>
      </View>
    </Modal>
  );
};

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: "rgba(5, 8, 14, 0.85)",
    justifyContent: "center",
    alignItems: "center",
    padding: 20,
  },
  card: {
    backgroundColor: colors.surface,
    borderRadius: 20,
    padding: 22,
    width: "100%",
    maxWidth: 420,
    borderWidth: 1.5,
    borderColor: colors.surfaceBorderActive,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 10 },
    shadowOpacity: 0.5,
    shadowRadius: 20,
    elevation: 10,
  },
  headerRow: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 14,
  },
  iconCircle: {
    width: 44,
    height: 44,
    borderRadius: 12,
    backgroundColor: colors.goldLight,
    justifyContent: "center",
    alignItems: "center",
    marginRight: 12,
    borderWidth: 1,
    borderColor: colors.surfaceBorderActive,
  },
  headerTitles: {
    flex: 1,
  },
  badgeRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
  },
  liveDot: {
    width: 5,
    height: 5,
    borderRadius: 2.5,
    backgroundColor: colors.gold,
  },
  badgeText: {
    fontSize: 9,
    fontWeight: "800",
    color: colors.gold,
    letterSpacing: 0.8,
  },
  title: {
    fontSize: 16,
    fontWeight: "800",
    color: colors.textPrimary,
    marginTop: 2,
  },
  closeBtn: {
    padding: 4,
  },
  description: {
    fontSize: 13,
    lineHeight: 19,
    color: colors.textSecondary,
    marginBottom: 16,
  },
  savingsBox: {
    backgroundColor: colors.emeraldLight,
    borderRadius: 12,
    padding: 12,
    borderWidth: 1,
    borderColor: colors.surfaceBorderEmerald,
    marginBottom: 16,
  },
  savingsHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    marginBottom: 2,
  },
  savingsLabel: {
    fontSize: 10,
    fontWeight: "800",
    letterSpacing: 0.8,
    color: colors.emerald,
  },
  savingsValue: {
    fontSize: 20,
    fontWeight: "800",
    color: colors.emerald,
    marginTop: 2,
    fontVariant: ["tabular-nums"],
  },
  changesSection: {
    backgroundColor: colors.surfaceLight,
    borderRadius: 12,
    padding: 14,
    marginBottom: 20,
    borderWidth: 1,
    borderColor: colors.surfaceBorder,
  },
  sectionHeading: {
    fontSize: 10,
    fontWeight: "800",
    letterSpacing: 0.8,
    color: colors.textSecondary,
    marginBottom: 10,
  },
  changeRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    marginBottom: 8,
    gap: 8,
  },
  changeText: {
    fontSize: 12,
    lineHeight: 17,
    color: colors.textPrimary,
    flex: 1,
  },
  actionsRow: {
    flexDirection: "row",
    gap: 12,
  },
  button: {
    flex: 1,
    paddingVertical: 13,
    borderRadius: 12,
    alignItems: "center",
    justifyContent: "center",
  },
  rejectButton: {
    backgroundColor: colors.surfaceLight,
    borderWidth: 1,
    borderColor: colors.surfaceBorderLight,
  },
  rejectText: {
    fontSize: 13,
    fontWeight: "700",
    color: colors.textSecondary,
  },
  approveButton: {
    backgroundColor: colors.gold,
    shadowColor: colors.gold,
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.35,
    shadowRadius: 6,
    elevation: 3,
  },
  approveText: {
    fontSize: 13,
    fontWeight: "800",
    color: colors.black,
    letterSpacing: 0.2,
  },
});
