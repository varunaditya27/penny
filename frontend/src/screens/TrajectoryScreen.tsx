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
    fetchTrajectoryData(parseFloat(simAmount) || 0, days);
  }, [days]);

  const handleApplySimulation = () => {
    const amt = parseFloat(simAmount) || 0;
    fetchTrajectoryData(amt, days);
  };

  const isSafe = trajectory?.is_safe ?? true;

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* Horizon Days Selector */}
      <View style={styles.tabRow}>
        {[30, 60, 90].map((d) => (
          <TouchableOpacity
            key={d}
            style={[styles.tab, days === d && styles.tabActive]}
            onPress={() => setDays(d)}
            activeOpacity={0.8}
          >
            <Text style={[styles.tabText, days === d && styles.tabTextActive]}>
              {d} Days Forecast
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Prospective Purchase Simulator Strip */}
      <View style={styles.simCard}>
        <Text style={styles.simHeading}>SIMULATE PROSPECTIVE OUTFLOW</Text>
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
            <Text style={styles.applyButtonText}>Simulate Dip</Text>
          </TouchableOpacity>
        </View>

        {/* Quick Amount Chips */}
        <View style={styles.chipRow}>
          {[100, 300, 500, 1200].map((chip) => (
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
            >
              <Text
                style={[
                  styles.chipText,
                  simAmount === chip.toString() && styles.chipTextActive,
                ]}
              >
                ${chip}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>

      {/* Trajectory Interactive Chart */}
      {loading ? (
        <View style={styles.loadingBox}>
          <ActivityIndicator size="large" color={colors.primary} />
          <Text style={styles.loadingText}>Computing 90-Day Simulation Ledger...</Text>
        </View>
      ) : trajectory ? (
        <>
          <TrajectoryChart
            points={trajectory.points}
            minimumReserve={trajectory.minimum_balance_to_keep}
            height={240}
          />

          {/* Core Trajectory Metrics */}
          <View style={styles.metricsGrid}>
            <View style={styles.gridCol}>
              <MetricCard
                label="Lowest Dip Point"
                value={`$${trajectory.lowest_projected_balance.toFixed(2)}`}
                subValue={`Occurs on: ${trajectory.lowest_balance_date}`}
                variant={isSafe ? "success" : "danger"}
                icon="📉"
              />
            </View>
            <View style={styles.gridCol}>
              <MetricCard
                label="Safety Buffer Status"
                value={isSafe ? "PROTECTED" : "BREACH RISK"}
                subValue={`Margin: +$${trajectory.buffer_margin.toFixed(2)}`}
                variant={isSafe ? "success" : "danger"}
                icon="🛡️"
              />
            </View>
          </View>

          {/* Liquidity Risk Guidance */}
          <View style={styles.guidanceCard}>
            <Text style={styles.guidanceTitle}>90-DAY FORECAST ANALYSIS</Text>
            <Text style={styles.guidanceText}>
              {isSafe
                ? `Penny's mathematical simulator verified that even with your recurring living expenses and scheduled bills, your daily balance remains safely above your $${trajectory.minimum_balance_to_keep.toLocaleString()} emergency reserve threshold.`
                : `⚠️ WARNING: This simulated expense causes your forward balance to drop into your emergency reserve buffer on ${trajectory.lowest_balance_date}. Consider spreading the expense into installments or delaying until your subsequent payday.`}
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
    backgroundColor: colors.surface,
    borderRadius: 12,
    padding: 4,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: colors.surfaceBorder,
  },
  tab: {
    flex: 1,
    paddingVertical: 8,
    alignItems: "center",
    borderRadius: 8,
  },
  tabActive: {
    backgroundColor: colors.surfaceLight,
  },
  tabText: {
    fontSize: 12,
    fontWeight: "600",
    color: colors.textSecondary,
  },
  tabTextActive: {
    color: colors.primary,
    fontWeight: "700",
  },
  simCard: {
    backgroundColor: colors.surface,
    borderRadius: 16,
    padding: 16,
    borderWidth: 1,
    borderColor: colors.surfaceBorder,
    marginBottom: 16,
  },
  simHeading: {
    fontSize: 10,
    fontWeight: "800",
    color: colors.textSecondary,
    letterSpacing: 0.8,
    marginBottom: 10,
  },
  simInputRow: {
    flexDirection: "row",
    gap: 10,
    marginBottom: 10,
  },
  inputWrap: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: colors.surfaceLight,
    borderRadius: 10,
    paddingHorizontal: 12,
    borderWidth: 1,
    borderColor: colors.surfaceBorder,
  },
  currencyPrefix: {
    fontSize: 16,
    fontWeight: "700",
    color: colors.textSecondary,
    marginRight: 4,
  },
  input: {
    flex: 1,
    fontSize: 16,
    fontWeight: "700",
    color: colors.textPrimary,
    paddingVertical: 10,
  },
  applyButton: {
    backgroundColor: colors.primary,
    paddingHorizontal: 16,
    justifyContent: "center",
    borderRadius: 10,
  },
  applyButtonText: {
    fontSize: 13,
    fontWeight: "700",
    color: colors.background,
  },
  chipRow: {
    flexDirection: "row",
    gap: 8,
  },
  chip: {
    paddingHorizontal: 12,
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
    fontSize: 11,
    fontWeight: "700",
    color: colors.textSecondary,
  },
  chipTextActive: {
    color: colors.primary,
  },
  loadingBox: {
    height: 240,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: colors.surface,
    borderRadius: 16,
    marginBottom: 16,
  },
  loadingText: {
    marginTop: 12,
    color: colors.textSecondary,
    fontSize: 12,
  },
  metricsGrid: {
    flexDirection: "row",
    gap: 10,
  },
  gridCol: {
    flex: 1,
  },
  guidanceCard: {
    backgroundColor: colors.surface,
    borderRadius: 14,
    padding: 16,
    borderWidth: 1,
    borderColor: colors.surfaceBorder,
    marginTop: 10,
  },
  guidanceTitle: {
    fontSize: 10,
    fontWeight: "800",
    color: colors.textSecondary,
    letterSpacing: 0.8,
    marginBottom: 6,
  },
  guidanceText: {
    fontSize: 13,
    lineHeight: 19,
    color: colors.textPrimary,
  },
});
