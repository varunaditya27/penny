import React from "react";
import { Modal, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { colors } from "../theme/colors";

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
              <Text style={styles.iconText}>🛡️</Text>
            </View>
            <View style={styles.headerTitles}>
              <Text style={styles.badgeText}>HUMAN-IN-THE-LOOP APPROVAL</Text>
              <Text style={styles.title}>Confirm Financial Mutation</Text>
            </View>
          </View>

          <Text style={styles.description}>{actionDescription}</Text>

          {estimatedSavings ? (
            <View style={styles.savingsBox}>
              <Text style={styles.savingsLabel}>UNLOCKED MONTHLY HEADROOM</Text>
              <Text style={styles.savingsValue}>
                +${estimatedSavings.toFixed(2)}/mo
              </Text>
            </View>
          ) : null}

          <View style={styles.changesSection}>
            <Text style={styles.sectionHeading}>PROPOSED ADJUSTMENTS:</Text>
            {proposedChanges.map((change, idx) => (
              <View key={idx} style={styles.changeRow}>
                <Text style={styles.changeBullet}>•</Text>
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
              <Text style={styles.approveText}>Approve Changes</Text>
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
    backgroundColor: "rgba(3, 7, 16, 0.8)",
    justifyContent: "center",
    alignItems: "center",
    padding: 20,
  },
  card: {
    backgroundColor: colors.surface,
    borderRadius: 20,
    padding: 20,
    width: "100%",
    maxWidth: 400,
    borderWidth: 1.5,
    borderColor: colors.warning,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.4,
    shadowRadius: 10,
    elevation: 8,
  },
  headerRow: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 14,
  },
  iconCircle: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: colors.warningLight,
    justifyContent: "center",
    alignItems: "center",
    marginRight: 12,
  },
  iconText: {
    fontSize: 20,
  },
  headerTitles: {
    flex: 1,
  },
  badgeText: {
    fontSize: 9,
    fontWeight: "800",
    color: colors.warning,
    letterSpacing: 0.8,
  },
  title: {
    fontSize: 16,
    fontWeight: "700",
    color: colors.textPrimary,
    marginTop: 2,
  },
  description: {
    fontSize: 13,
    lineHeight: 19,
    color: colors.textSecondary,
    marginBottom: 14,
  },
  savingsBox: {
    backgroundColor: colors.surfaceLight,
    padding: 12,
    borderRadius: 10,
    marginBottom: 14,
    borderLeftWidth: 3,
    borderLeftColor: colors.success,
  },
  savingsLabel: {
    fontSize: 10,
    fontWeight: "700",
    color: colors.textMuted,
    letterSpacing: 0.5,
  },
  savingsValue: {
    fontSize: 18,
    fontWeight: "800",
    color: colors.success,
    marginTop: 2,
  },
  changesSection: {
    backgroundColor: colors.surfaceLight,
    padding: 12,
    borderRadius: 10,
    marginBottom: 18,
  },
  sectionHeading: {
    fontSize: 10,
    fontWeight: "700",
    color: colors.textMuted,
    letterSpacing: 0.5,
    marginBottom: 6,
  },
  changeRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    marginBottom: 4,
  },
  changeBullet: {
    color: colors.primary,
    fontSize: 14,
    marginRight: 6,
    lineHeight: 18,
  },
  changeText: {
    flex: 1,
    fontSize: 12,
    color: colors.textPrimary,
    lineHeight: 17,
  },
  actionsRow: {
    flexDirection: "row",
    gap: 10,
  },
  button: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: 10,
    alignItems: "center",
  },
  rejectButton: {
    backgroundColor: colors.surfaceLight,
    borderWidth: 1,
    borderColor: colors.surfaceBorder,
  },
  rejectText: {
    fontSize: 13,
    fontWeight: "700",
    color: colors.textSecondary,
  },
  approveButton: {
    backgroundColor: colors.primary,
  },
  approveText: {
    fontSize: 13,
    fontWeight: "700",
    color: colors.background,
  },
});
