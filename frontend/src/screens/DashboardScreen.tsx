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
import { ReserveGauge } from "../components/ReserveGauge";
import {
  ArrowDownLeft,
  ArrowUpRight,
  Calendar,
  CreditCard,
  Flame,
  Lock,
  Scissors,
  ShieldCheck,
  Sparkle,
  TrendUp,
  Wallet,
} from "../components/icons";

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
        <ActivityIndicator size="large" color={colors.emerald} />
        <Text style={styles.loadingText}>Loading accounts and balances...</Text>
      </View>
    );
  }

  const availableBal = profile?.current_available_balance || 0;
  const reserveMin = profile?.minimum_balance_to_keep || 0;
  const reserveHeadroom = availableBal - reserveMin;
  const isBufferSafe = reserveHeadroom >= 0;

  // Proportional Inflow vs Outflow Cashflow Metrics
  const monthlyIncome = profile?.risk_metrics?.monthly_confirmed_income || 0;
  const monthlyBurn = profile?.risk_metrics?.monthly_fixed_burn_rate || 0;
  const totalFlow = monthlyIncome + monthlyBurn;
  const inflowRatio = totalFlow > 0 ? (monthlyIncome / totalFlow) * 100 : 50;

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={onRefresh}
          tintColor={colors.emerald}
        />
      }
    >
      {/* Financial Command Center Hero Card */}
      <View style={styles.heroCard}>
        <View style={styles.heroTopRow}>
          <View style={styles.heroMainInfo}>
            <View style={styles.labelRow}>
              <Wallet size={15} color={colors.gold} weight="duotone" />
              <Text style={styles.heroLabel}>AVAILABLE CASH</Text>
            </View>
            <Text style={styles.heroBalance}>
              ${availableBal.toLocaleString("en-US", {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}
            </Text>
            <View style={styles.headroomPill}>
              <ShieldCheck
                size={14}
                color={isBufferSafe ? colors.emerald : colors.danger}
                weight="duotone"
              />
              <Text
                style={[
                  styles.headroomText,
                  { color: isBufferSafe ? colors.emerald : colors.danger },
                ]}
              >
                {isBufferSafe ? "+" : ""}${reserveHeadroom.toLocaleString("en-US", {
                  minimumFractionDigits: 2,
                })}{" "}
                Above Reserve Target
              </Text>
            </View>
          </View>

          {/* Integrated Circular SVG Reserve Gauge */}
          <View style={styles.heroGaugeWrap}>
            <ReserveGauge
              availableBalance={availableBal}
              minimumReserve={reserveMin}
              size={116}
              strokeWidth={9}
            />
          </View>
        </View>

        {/* Proportional Inflow vs Outflow Bar */}
        {monthlyIncome > 0 && (
          <View style={styles.flowSection}>
            <View style={styles.flowLabels}>
              <View style={styles.flowLabelItem}>
                <ArrowUpRight size={12} color={colors.emerald} weight="bold" />
                <Text style={styles.flowText}>Monthly Income: ${monthlyIncome.toLocaleString()}</Text>
              </View>
              <View style={styles.flowLabelItem}>
                <ArrowDownLeft size={12} color={colors.gold} weight="bold" />
                <Text style={styles.flowText}>Fixed Expenses: ${monthlyBurn.toLocaleString()}</Text>
              </View>
            </View>
            <View style={styles.flowBarTrack}>
              <View
                style={[
                  styles.flowBarSegmentInflow,
                  { width: `${Math.min(100, Math.max(10, inflowRatio))}%` },
                ]}
              />
              <View
                style={[
                  styles.flowBarSegmentOutflow,
                  { width: `${Math.min(90, Math.max(0, 100 - inflowRatio))}%` },
                ]}
              />
            </View>
          </View>
        )}

        <View style={styles.heroFooter}>
          <View style={styles.heroSubItem}>
            <Text style={styles.heroSubLabel}>Emergency Fund Target</Text>
            <Text style={styles.heroSubValue}>
              ${reserveMin.toLocaleString()}
            </Text>
          </View>
          <View style={styles.heroSubDivider} />
          <View style={styles.heroSubItem}>
            <Text style={styles.heroSubLabel}>Savings Status</Text>
            <Text
              style={[
                styles.heroSubValue,
                { color: isBufferSafe ? colors.emerald : colors.danger },
              ]}
            >
              {isBufferSafe ? "HEALTHY" : "BELOW TARGET"}
            </Text>
          </View>
        </View>
      </View>

      {/* Quick Action Navigation Chips */}
      <View style={styles.actionRow}>
        <TouchableOpacity
          style={styles.actionButton}
          onPress={() => onNavigate("affordability")}
          activeOpacity={0.8}
        >
          <CreditCard size={18} color={colors.gold} weight="duotone" />
          <Text style={styles.actionText}>Can I Afford?</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.actionButton}
          onPress={() => onNavigate("trajectory")}
          activeOpacity={0.8}
        >
          <TrendUp size={18} color={colors.sky} weight="duotone" />
          <Text style={styles.actionText}>90d Forecast</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.actionButton, styles.actionButtonHighlight]}
          onPress={() => onNavigate("chat")}
          activeOpacity={0.8}
        >
          <Sparkle size={18} color={colors.violet} weight="fill" />
          <Text style={[styles.actionText, { color: colors.violet }]}>
            Ask Penny
          </Text>
        </TouchableOpacity>
      </View>

      {/* 30-Day Cash Flow Bento Grid */}
      {profile?.risk_metrics ? (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>MONTHLY CASH FLOW</Text>
          <View style={styles.gridRow}>
            <View style={styles.gridCol}>
              <MetricCard
                label="Monthly Income"
                value={`$${profile.risk_metrics.monthly_confirmed_income.toLocaleString()}`}
                icon={<ArrowUpRight size={16} color={colors.emerald} weight="bold" />}
                variant="success"
              />
            </View>
            <View style={styles.gridCol}>
              <MetricCard
                label="Fixed Bills"
                value={`$${profile.risk_metrics.monthly_fixed_burn_rate.toLocaleString()}`}
                icon={<Flame size={16} color={colors.gold} weight="duotone" />}
                variant="warning"
              />
            </View>
          </View>
          <MetricCard
            label="Free Cash Flow"
            value={`$${profile.risk_metrics.discretionary_cashflow.toLocaleString()}`}
            subValue={`Fixed expenses take ${(profile.risk_metrics.fixed_cost_ratio * 100).toFixed(0)}% of income`}
            icon={<Wallet size={16} color={colors.sky} weight="duotone" />}
            variant="default"
          />
        </View>
      ) : null}

      {/* Spending Policies Card */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>BUDGET PRIORITIES</Text>
        <View style={styles.policyCard}>
          <View style={styles.policyRow}>
            <View style={styles.policyHeaderRow}>
              <Lock size={14} color={colors.emerald} weight="duotone" />
              <Text style={styles.policyTagLabel}>PROTECTED ESSENTIALS</Text>
            </View>
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

          <View style={[styles.policyRow, { marginTop: 14 }]}>
            <View style={styles.policyHeaderRow}>
              <Scissors size={14} color={colors.gold} weight="duotone" />
              <Text style={[styles.policyTagLabel, { color: colors.gold }]}>
                FLEXIBLE EXPENSES
              </Text>
            </View>
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

      {/* Upcoming Financial Commitments */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>UPCOMING BILLS & PAYDAYS</Text>
        {events.slice(0, 5).map((evt) => {
          const isIncome = evt.amount > 0;
          return (
            <View key={evt.event_id} style={styles.eventRow}>
              <View style={styles.eventIconContainer}>
                {isIncome ? (
                  <ArrowUpRight size={16} color={colors.emerald} weight="bold" />
                ) : (
                  <ArrowDownLeft size={16} color={colors.textSecondary} weight="bold" />
                )}
              </View>
              <View style={styles.eventLeft}>
                <Text style={styles.eventCategory}>{evt.category}</Text>
                <Text style={styles.eventDesc}>{evt.description}</Text>
                <View style={styles.eventDateRow}>
                  <Calendar size={11} color={colors.textMuted} weight="duotone" />
                  <Text style={styles.eventDate}>{evt.event_date}</Text>
                </View>
              </View>
              <View style={styles.eventRight}>
                <Text
                  style={[
                    styles.eventAmount,
                    { color: isIncome ? colors.emerald : colors.textPrimary },
                  ]}
                >
                  {isIncome ? "+" : ""}${Math.abs(evt.amount).toFixed(2)}
                </Text>
                {evt.is_recurring ? (
                  <View style={styles.recurringBadge}>
                    <Text style={styles.recurringTag}>Recurring</Text>
                  </View>
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
    backgroundColor: colors.surfaceCard,
    borderRadius: 22,
    padding: 20,
    borderWidth: 1.5,
    borderColor: colors.surfaceBorderLight,
    marginBottom: 16,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.4,
    shadowRadius: 14,
    elevation: 6,
  },
  heroTopRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  heroMainInfo: {
    flex: 1,
    paddingRight: 8,
  },
  heroGaugeWrap: {
    alignItems: "center",
    justifyContent: "center",
  },
  labelRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    marginBottom: 4,
  },
  heroLabel: {
    fontSize: 10,
    fontWeight: "800",
    color: colors.textSecondary,
    letterSpacing: 0.8,
  },
  heroBalance: {
    fontSize: 28,
    fontWeight: "900",
    color: colors.textPrimary,
    letterSpacing: -0.5,
    fontVariant: ["tabular-nums"],
    marginVertical: 4,
  },
  headroomPill: {
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
    marginTop: 4,
  },
  headroomText: {
    fontSize: 12,
    fontWeight: "700",
    letterSpacing: 0.3,
  },
  flowSection: {
    marginTop: 16,
    paddingTop: 14,
    borderTopWidth: 1,
    borderTopColor: colors.surfaceBorder,
  },
  flowLabels: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: 6,
  },
  flowLabelItem: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
  },
  flowText: {
    fontSize: 11,
    fontWeight: "600",
    color: colors.textMuted,
  },
  flowBarTrack: {
    height: 6,
    borderRadius: 3,
    backgroundColor: colors.surfaceLight,
    flexDirection: "row",
    overflow: "hidden",
  },
  flowBarSegmentInflow: {
    height: "100%",
    backgroundColor: colors.emerald,
    borderRadius: 3,
  },
  flowBarSegmentOutflow: {
    height: "100%",
    backgroundColor: colors.gold,
    borderRadius: 3,
  },
  heroFooter: {
    flexDirection: "row",
    marginTop: 16,
    paddingTop: 14,
    borderTopWidth: 1,
    borderTopColor: colors.surfaceBorder,
  },
  heroSubItem: {
    flex: 1,
  },
  heroSubLabel: {
    fontSize: 10,
    fontWeight: "600",
    color: colors.textMuted,
    marginBottom: 3,
  },
  heroSubValue: {
    fontSize: 14,
    fontWeight: "800",
    color: colors.textPrimary,
    fontVariant: ["tabular-nums"],
  },
  heroSubDivider: {
    width: 1,
    height: 24,
    backgroundColor: colors.surfaceBorder,
    marginHorizontal: 12,
  },
  actionRow: {
    flexDirection: "row",
    gap: 8,
    marginBottom: 16,
  },
  actionButton: {
    flex: 1,
    backgroundColor: colors.surfaceCard,
    borderRadius: 14,
    paddingVertical: 12,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 1,
    borderColor: colors.surfaceBorder,
    gap: 4,
  },
  actionButtonHighlight: {
    borderColor: colors.violetLight,
    backgroundColor: "rgba(139, 92, 246, 0.08)",
  },
  actionText: {
    fontSize: 11,
    fontWeight: "700",
    color: colors.textPrimary,
  },
  section: {
    marginBottom: 16,
  },
  sectionTitle: {
    fontSize: 11,
    fontWeight: "800",
    letterSpacing: 1,
    color: colors.textSecondary,
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
    backgroundColor: colors.surfaceCard,
    borderRadius: 16,
    padding: 16,
    borderWidth: 1,
    borderColor: colors.surfaceBorder,
  },
  policyRow: {},
  policyHeaderRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    marginBottom: 8,
  },
  policyTagLabel: {
    fontSize: 10,
    fontWeight: "800",
    color: colors.emerald,
    letterSpacing: 0.8,
  },
  tagWrap: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 6,
  },
  protectedTag: {
    backgroundColor: colors.emeraldLight,
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.surfaceBorderEmerald,
  },
  protectedTagText: {
    fontSize: 11,
    fontWeight: "700",
    color: colors.emerald,
  },
  flexibleTag: {
    backgroundColor: colors.goldLight,
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.surfaceBorderActive,
  },
  flexibleTagText: {
    fontSize: 11,
    fontWeight: "700",
    color: colors.gold,
  },
  eventRow: {
    backgroundColor: colors.surfaceCard,
    borderRadius: 14,
    padding: 14,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: colors.surfaceBorder,
    flexDirection: "row",
    alignItems: "center",
  },
  eventIconContainer: {
    width: 32,
    height: 32,
    borderRadius: 10,
    backgroundColor: colors.surfaceLight,
    alignItems: "center",
    justifyContent: "center",
    marginRight: 12,
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
    marginTop: 1,
  },
  eventDateRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    marginTop: 3,
  },
  eventDate: {
    fontSize: 10,
    color: colors.textMuted,
  },
  eventRight: {
    alignItems: "flex-end",
  },
  eventAmount: {
    fontSize: 14,
    fontWeight: "800",
    fontVariant: ["tabular-nums"],
  },
  recurringBadge: {
    backgroundColor: colors.surfaceLight,
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 6,
    marginTop: 4,
  },
  recurringTag: {
    fontSize: 9,
    fontWeight: "700",
    color: colors.textSecondary,
    letterSpacing: 0.3,
  },
});
