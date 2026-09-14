import React, { useEffect, useState } from "react";
import {
  ActivityIndicator,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { FinancialEvent, UserProfile } from "../types";
import { api } from "../services/api";
import { colors } from "../theme/colors";
import { MetricCard } from "../components/MetricCard";

interface DashboardScreenProps {
  onNavigate: (tab: "dashboard" | "trajectory" | "affordability" | "chat") => void;
}

export const DashboardScreen: React.FC<DashboardScreenProps> = ({ onNavigate }) => {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [events, setEvents] = useState<FinancialEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadData = async () => {
    try {
      const [profData, evtsData] = await Promise.all([
        api.fetchUserProfile("user_01"),
        api.fetchUserEvents("user_01"),
      ]);
      setProfile(profData);
      setEvents(evtsData);
    } catch (err) {
      console.error("Failed to load dashboard data", err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const onRefresh = () => {
    setRefreshing(true);
    loadData();
  };

  if (loading) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color={colors.primary} />
        <Text style={styles.loadingText}>Loading Financial Dashboard...</Text>
      </View>
    );
  }

  const reserveHeadroom =
    (profile?.current_available_balance || 0) -
    (profile?.minimum_balance_to_keep || 0);
  const isBufferSafe = reserveHeadroom >= 0;

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={onRefresh}
          tintColor={colors.primary}
        />
      }
    >
      {/* Hero Financial Health Card */}
      <View style={styles.heroCard}>
        <View style={styles.heroHeader}>
          <Text style={styles.heroLabel}>CURRENT AVAILABLE LIQUIDITY</Text>
          <View
            style={[
              styles.healthBadge,
              {
                backgroundColor: isBufferSafe
                  ? colors.successLight
                  : colors.dangerLight,
              },
            ]}
          >
            <Text
              style={[
                styles.healthBadgeText,
                { color: isBufferSafe ? colors.success : colors.danger },
              ]}
            >
              {isBufferSafe ? "SHIELD INTACT" : "BUFFER DEFICIT"}
            </Text>
          </View>
        </View>

        <Text style={styles.heroBalance}>
          ${(profile?.current_available_balance || 0).toLocaleString("en-US", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
          })}
        </Text>

        <View style={styles.heroFooter}>
          <View style={styles.heroSubItem}>
            <Text style={styles.heroSubLabel}>Emergency Reserve Target</Text>
            <Text style={styles.heroSubValue}>
              ${(profile?.minimum_balance_to_keep || 0).toLocaleString()}
            </Text>
          </View>
          <View style={styles.heroSubDivider} />
          <View style={styles.heroSubItem}>
            <Text style={styles.heroSubLabel}>Free Reserve Headroom</Text>
            <Text
              style={[
                styles.heroSubValue,
                { color: isBufferSafe ? colors.success : colors.danger },
              ]}
            >
              +${reserveHeadroom.toLocaleString("en-US", {
                minimumFractionDigits: 2,
              })}
            </Text>
          </View>
        </View>
      </View>

      {/* Quick Action Buttons */}
      <View style={styles.actionRow}>
        <TouchableOpacity
          style={styles.actionButton}
          onPress={() => onNavigate("affordability")}
          activeOpacity={0.8}
        >
          <Text style={styles.actionIcon}>💳</Text>
          <Text style={styles.actionText}>Can I Afford?</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.actionButton}
          onPress={() => onNavigate("trajectory")}
          activeOpacity={0.8}
        >
          <Text style={styles.actionIcon}>📈</Text>
          <Text style={styles.actionText}>90d Trajectory</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.actionButton, styles.actionButtonHighlight]}
          onPress={() => onNavigate("chat")}
          activeOpacity={0.8}
        >
          <Text style={styles.actionIcon}>🤖</Text>
          <Text style={[styles.actionText, { color: colors.accent }]}>
            Ask Penny
          </Text>
        </TouchableOpacity>
      </View>

      {/* Cash Flow Risk Metrics */}
      {profile?.risk_metrics ? (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>30-DAY CASH FLOW METRICS</Text>
          <View style={styles.gridRow}>
            <View style={styles.gridCol}>
              <MetricCard
                label="Monthly Income"
                value={`$${profile.risk_metrics.monthly_confirmed_income.toLocaleString()}`}
                icon="💵"
                variant="success"
              />
            </View>
            <View style={styles.gridCol}>
              <MetricCard
                label="Fixed Burn Rate"
                value={`$${profile.risk_metrics.monthly_fixed_burn_rate.toLocaleString()}`}
                icon="🔥"
                variant="warning"
              />
            </View>
          </View>
          <MetricCard
            label="Discretionary Surplus"
            value={`$${profile.risk_metrics.discretionary_cashflow.toLocaleString()}`}
            subValue={`Fixed cost ratio: ${(profile.risk_metrics.fixed_cost_ratio * 100).toFixed(0)}% of confirmed income`}
            icon="💎"
            variant="accent"
          />
        </View>
      ) : null}

      {/* Protected vs Flexible Categories */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>SPENDING POLICIES</Text>
        <View style={styles.policyCard}>
          <View style={styles.policyRow}>
            <Text style={styles.policyTagLabel}>🛡️ PROTECTED ESSENTIALS</Text>
            <View style={styles.tagWrap}>
              {(profile?.expense_categories_to_protect || ["Rent", "Healthcare"]).map(
                (cat, idx) => (
                  <View key={idx} style={styles.protectedTag}>
                    <Text style={styles.protectedTagText}>{cat}</Text>
                  </View>
                )
              )}
            </View>
          </View>

          <View style={[styles.policyRow, { marginTop: 12 }]}>
            <Text style={styles.policyTagLabel}>✂️ FLEXIBLE FOR CUTBACKS</Text>
            <View style={styles.tagWrap}>
              {(profile?.expense_categories_to_reduce || ["Dining", "Coffee"]).map(
                (cat, idx) => (
                  <View key={idx} style={styles.flexibleTag}>
                    <Text style={styles.flexibleTagText}>{cat}</Text>
                  </View>
                )
              )}
            </View>
          </View>
        </View>
      </View>

      {/* Recent / Upcoming Ledger Events */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>UPCOMING FINANCIAL COMMITMENTS</Text>
        {events.slice(0, 5).map((evt) => {
          const isIncome = evt.amount > 0;
          return (
            <View key={evt.event_id} style={styles.eventRow}>
              <View style={styles.eventLeft}>
                <Text style={styles.eventCategory}>{evt.category}</Text>
                <Text style={styles.eventDesc}>{evt.description}</Text>
                <Text style={styles.eventDate}>{evt.event_date}</Text>
              </View>
              <View style={styles.eventRight}>
                <Text
                  style={[
                    styles.eventAmount,
                    { color: isIncome ? colors.success : colors.textPrimary },
                  ]}
                >
                  {isIncome ? "+" : ""}${Math.abs(evt.amount).toFixed(2)}
                </Text>
                {evt.is_recurring ? (
                  <Text style={styles.recurringTag}>Recurring</Text>
                ) : null}
              </View>
            </View>
          );
        })}
      </View>
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
  centerContainer: {
    flex: 1,
    backgroundColor: colors.background,
    justifyContent: "center",
    alignItems: "center",
  },
  loadingText: {
    marginTop: 12,
    color: colors.textSecondary,
    fontSize: 13,
  },
  heroCard: {
    backgroundColor: colors.surface,
    borderRadius: 20,
    padding: 20,
    borderWidth: 1,
    borderColor: colors.surfaceBorder,
    marginBottom: 16,
  },
  heroHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  heroLabel: {
    fontSize: 11,
    fontWeight: "700",
    color: colors.textSecondary,
    letterSpacing: 0.8,
  },
  healthBadge: {
    paddingHorizontal: 10,
    paddingVertical: 3,
    borderRadius: 12,
  },
  healthBadgeText: {
    fontSize: 10,
    fontWeight: "800",
    letterSpacing: 0.5,
  },
  heroBalance: {
    fontSize: 36,
    fontWeight: "900",
    color: colors.textPrimary,
    marginVertical: 12,
    letterSpacing: -0.5,
  },
  heroFooter: {
    flexDirection: "row",
    backgroundColor: colors.surfaceLight,
    borderRadius: 12,
    padding: 12,
    alignItems: "center",
  },
  heroSubItem: {
    flex: 1,
  },
  heroSubDivider: {
    width: 1,
    height: 24,
    backgroundColor: colors.surfaceBorder,
    marginHorizontal: 8,
  },
  heroSubLabel: {
    fontSize: 10,
    color: colors.textMuted,
    fontWeight: "600",
    marginBottom: 2,
  },
  heroSubValue: {
    fontSize: 14,
    fontWeight: "800",
    color: colors.textPrimary,
  },
  actionRow: {
    flexDirection: "row",
    gap: 10,
    marginBottom: 20,
  },
  actionButton: {
    flex: 1,
    backgroundColor: colors.surface,
    borderRadius: 14,
    paddingVertical: 12,
    alignItems: "center",
    borderWidth: 1,
    borderColor: colors.surfaceBorder,
  },
  actionButtonHighlight: {
    borderColor: colors.accent,
  },
  actionIcon: {
    fontSize: 18,
    marginBottom: 4,
  },
  actionText: {
    fontSize: 11,
    fontWeight: "700",
    color: colors.textSecondary,
  },
  section: {
    marginBottom: 20,
  },
  sectionTitle: {
    fontSize: 11,
    fontWeight: "800",
    color: colors.textSecondary,
    letterSpacing: 1,
    marginBottom: 10,
  },
  gridRow: {
    flexDirection: "row",
    gap: 10,
  },
  gridCol: {
    flex: 1,
  },
  policyCard: {
    backgroundColor: colors.surface,
    borderRadius: 14,
    padding: 16,
    borderWidth: 1,
    borderColor: colors.surfaceBorder,
  },
  policyRow: {},
  policyTagLabel: {
    fontSize: 10,
    fontWeight: "700",
    color: colors.textMuted,
    marginBottom: 6,
  },
  tagWrap: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 6,
  },
  protectedTag: {
    backgroundColor: "rgba(16, 185, 129, 0.12)",
    borderWidth: 1,
    borderColor: "rgba(16, 185, 129, 0.3)",
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 8,
  },
  protectedTagText: {
    color: colors.success,
    fontSize: 11,
    fontWeight: "600",
  },
  flexibleTag: {
    backgroundColor: "rgba(245, 158, 11, 0.12)",
    borderWidth: 1,
    borderColor: "rgba(245, 158, 11, 0.3)",
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 8,
  },
  flexibleTagText: {
    color: colors.warning,
    fontSize: 11,
    fontWeight: "600",
  },
  eventRow: {
    backgroundColor: colors.surface,
    borderRadius: 12,
    padding: 14,
    marginBottom: 8,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    borderWidth: 1,
    borderColor: colors.surfaceBorder,
  },
  eventLeft: {
    flex: 1,
  },
  eventCategory: {
    fontSize: 13,
    fontWeight: "700",
    color: colors.textPrimary,
  },
  eventDesc: {
    fontSize: 11,
    color: colors.textSecondary,
    marginTop: 2,
  },
  eventDate: {
    fontSize: 10,
    color: colors.textMuted,
    marginTop: 3,
  },
  eventRight: {
    alignItems: "flex-end",
  },
  eventAmount: {
    fontSize: 14,
    fontWeight: "800",
  },
  recurringTag: {
    fontSize: 9,
    color: colors.primary,
    backgroundColor: "rgba(56, 189, 248, 0.1)",
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 6,
    marginTop: 4,
    fontWeight: "600",
  },
});
