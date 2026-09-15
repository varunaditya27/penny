import React, { useEffect, useState } from "react";
import {
  ActivityIndicator,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { TrajectoryResponse } from "../types";
import { api } from "../services/api";
import { colors } from "../theme/colors";
import { TrajectoryChart } from "../components/TrajectoryChart";
import { MetricCard } from "../components/MetricCard";
import {
  Calendar,
  CheckCircle,
  Info,
  ShieldCheck,
  Sparkle,
  TrendUp,
  WarningCircle,
} from "../components/icons";

export const TrajectoryScreen: React.FC = () => {
  const [trajectory, setTrajectory] = useState<TrajectoryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [simAmount, setSimAmount] = useState<string>("0");
  const [days, setDays] = useState<number>(90);

  const fetchTrajectoryData = async (amount: number, horizonDays: number) => {
    setLoading(true);
    try {
      const data = await api.fetchCashflowTrajectory(
        "user_01",
        amount > 0 ? amount : undefined,
        horizonDays
      );
      setTrajectory(data);
    } catch (err) {
      console.error("Error loading trajectory", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    (async () => {
      try {
        const amt = parseFloat(simAmount) || 0;
        const data = await api.fetchCashflowTrajectory(
          "user_01",
          amt > 0 ? amt : undefined,
          days
        );
        if (isMounted) setTrajectory(data);
      } catch (err) {
        console.error("Error loading trajectory", err);
      } finally {
        if (isMounted) setLoading(false);
      }
    })();
    return () => {
      isMounted = false;
    };
  }, [days]);

  const handleApplySimulation = () => {
    const amt = parseFloat(simAmount) || 0;
    fetchTrajectoryData(amt, days);
  };

  const isSafe = trajectory?.is_safe ?? true;
  const quickChips = [250, 500, 1000, 2500];

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* Horizon Glass Pill Selector */}
      <View style={styles.tabRow}>
        {[30, 60, 90].map((d) => (
          <TouchableOpacity
            key={d}
            style={[styles.tab, days === d && styles.tabActive]}
            onPress={() => setDays(d)}
            activeOpacity={0.8}
          >
            <View style={styles.tabContentRow}>
              <Calendar
                size={13}
                color={days === d ? colors.sky : colors.textMuted}
                weight={days === d ? "duotone" : "regular"}
              />
              <Text style={[styles.tabText, days === d && styles.tabTextActive]}>
                {d} Days
              </Text>
            </View>
          </TouchableOpacity>
        ))}
      </View>

      {/* Prospective Purchase Simulator Strip */}
      <View style={styles.simCard}>
        <View style={styles.simHeader}>
          <Sparkle size={14} color={colors.sky} weight="fill" />
          <Text style={styles.simHeading}>TEST A PURCHASE AMOUNT</Text>
        </View>
        <View style={styles.simInputRow}>
          <View style={styles.inputWrap}>
            <Text style={styles.currencyPrefix}>$</Text>
            <TextInput
              style={styles.input}
              value={simAmount}
              onChangeText={setSimAmount}
              keyboardType="numeric"
              placeholder="0.00"
              placeholderTextColor={colors.textMuted}
            />
          </View>
          <TouchableOpacity
            style={styles.applyButton}
            onPress={handleApplySimulation}
            activeOpacity={0.8}
          >
            <Text style={styles.applyButtonText}>Preview Impact</Text>
          </TouchableOpacity>
        </View>

        {/* Quick Amount Chips */}
        <View style={styles.chipRow}>
          {quickChips.map((chip) => (
            <TouchableOpacity
              key={chip}
              style={[
                styles.chip,
                simAmount === chip.toString() && styles.chipActive,
              ]}
              onPress={() => {
                setSimAmount(chip.toString());
                fetchTrajectoryData(chip, days);
              }}
              activeOpacity={0.8}
            >
              <Text
                style={[
                  styles.chipText,
                  simAmount === chip.toString() && styles.chipTextActive,
                ]}
              >
                ${chip.toLocaleString()}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>

      {/* Trajectory Interactive Chart */}
      {loading ? (
        <View style={styles.loadingBox}>
          <ActivityIndicator size="large" color={colors.sky} />
          <Text style={styles.loadingText}>Forecasting {days}-day cash flow...</Text>
        </View>
      ) : trajectory ? (
        <>
          <TrajectoryChart
            points={trajectory.points}
            minimumReserve={trajectory.minimum_balance_to_keep}
            height={240}
          />

          {/* Core Trajectory Bento Metrics */}
          <View style={styles.metricsGrid}>
            <View style={styles.gridCol}>
              <MetricCard
                label="Lowest Projected Balance"
                value={`$${trajectory.lowest_projected_balance.toFixed(2)}`}
                subValue={`Occurs on: ${trajectory.lowest_balance_date}`}
                variant={isSafe ? "success" : "danger"}
                icon={
                  <TrendUp
                    size={16}
                    color={isSafe ? colors.emerald : colors.danger}
                    weight="bold"
                  />
                }
              />
            </View>
            <View style={styles.gridCol}>
              <MetricCard
                label="Emergency Fund"
                value={isSafe ? "HEALTHY" : "BELOW TARGET"}
                subValue={`Margin: +$${trajectory.buffer_margin.toFixed(2)}`}
                variant={isSafe ? "success" : "danger"}
                icon={
                  <ShieldCheck
                    size={16}
                    color={isSafe ? colors.emerald : colors.danger}
                    weight="duotone"
                  />
                }
              />
            </View>
          </View>

          {/* Liquidity Risk Guidance */}
          <View
            style={[
              styles.guidanceCard,
              !isSafe && styles.guidanceCardAlert,
            ]}
          >
            <View style={styles.guidanceHeader}>
              {isSafe ? (
                <CheckCircle size={16} color={colors.emerald} weight="duotone" />
              ) : (
                <WarningCircle size={16} color={colors.danger} weight="duotone" />
              )}
              <Text
                style={[
                  styles.guidanceTitle,
                  { color: isSafe ? colors.emerald : colors.danger },
                ]}
              >
                {isSafe
                  ? `${days}-DAY FORECAST: HEALTHY`
                  : "POTENTIAL LOW BALANCE ALERT"}
              </Text>
            </View>
            <Text style={styles.guidanceText}>
              {isSafe
                ? `Your projected balance stays safely above your $${trajectory.minimum_balance_to_keep.toLocaleString()} emergency fund target across all upcoming scheduled bills and living expenses.`
                : `This purchase causes your balance to dip below your $${trajectory.minimum_balance_to_keep.toLocaleString()} emergency fund target on ${trajectory.lowest_balance_date}. Consider splitting this into installments or waiting until after your next payday.`}
            </Text>
          </View>
        </>
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
  tabRow: {
    flexDirection: "row",
    backgroundColor: colors.surfaceCard,
    borderRadius: 14,
    padding: 4,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: colors.surfaceBorder,
  },
  tab: {
    flex: 1,
    paddingVertical: 10,
    alignItems: "center",
    borderRadius: 10,
  },
  tabActive: {
    backgroundColor: colors.surfaceLight,
    borderWidth: 1,
    borderColor: colors.surfaceBorderLight,
  },
  tabContentRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  tabText: {
    fontSize: 12,
    fontWeight: "700",
    color: colors.textSecondary,
  },
  tabTextActive: {
    color: colors.sky,
  },
  simCard: {
    backgroundColor: colors.surfaceCard,
    borderRadius: 18,
    padding: 18,
    borderWidth: 1.5,
    borderColor: colors.surfaceBorder,
    marginBottom: 16,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.35,
    shadowRadius: 10,
    elevation: 4,
  },
  simHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    marginBottom: 12,
  },
  simHeading: {
    fontSize: 10,
    fontWeight: "800",
    color: colors.sky,
    letterSpacing: 0.8,
  },
  simInputRow: {
    flexDirection: "row",
    gap: 10,
  },
  inputWrap: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: colors.surfaceLight,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.surfaceBorder,
    paddingHorizontal: 12,
  },
  currencyPrefix: {
    fontSize: 18,
    fontWeight: "800",
    color: colors.sky,
    marginRight: 6,
  },
  input: {
    flex: 1,
    fontSize: 18,
    fontWeight: "800",
    color: colors.textPrimary,
    paddingVertical: 10,
    fontVariant: ["tabular-nums"],
  },
  applyButton: {
    backgroundColor: colors.sky,
    borderRadius: 12,
    paddingHorizontal: 18,
    justifyContent: "center",
    alignItems: "center",
  },
  applyButtonText: {
    fontSize: 12,
    fontWeight: "800",
    color: colors.black,
    letterSpacing: 0.3,
  },
  chipRow: {
    flexDirection: "row",
    gap: 8,
    marginTop: 10,
  },
  chip: {
    flex: 1,
    paddingVertical: 7,
    backgroundColor: colors.surfaceLight,
    borderRadius: 8,
    alignItems: "center",
    borderWidth: 1,
    borderColor: colors.surfaceBorder,
  },
  chipActive: {
    backgroundColor: colors.skyLight,
    borderColor: colors.skyGlow,
  },
  chipText: {
    fontSize: 11,
    fontWeight: "700",
    color: colors.textSecondary,
    fontVariant: ["tabular-nums"],
  },
  chipTextActive: {
    color: colors.sky,
  },
  loadingBox: {
    height: 240,
    justifyContent: "center",
    alignItems: "center",
  },
  loadingText: {
    marginTop: 12,
    fontSize: 12,
    color: colors.textSecondary,
  },
  metricsGrid: {
    flexDirection: "row",
    gap: 10,
    marginTop: 16,
  },
  gridCol: {
    flex: 1,
  },
  guidanceCard: {
    backgroundColor: colors.surfaceCard,
    borderRadius: 16,
    padding: 16,
    borderWidth: 1,
    borderColor: colors.surfaceBorderEmerald,
    marginTop: 12,
  },
  guidanceCardAlert: {
    borderColor: colors.dangerLight,
    backgroundColor: "rgba(239, 68, 68, 0.06)",
  },
  guidanceHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    marginBottom: 8,
  },
  guidanceTitle: {
    fontSize: 11,
    fontWeight: "800",
    letterSpacing: 0.8,
  },
  guidanceText: {
    fontSize: 12,
    lineHeight: 18,
    color: colors.textSecondary,
  },
});
