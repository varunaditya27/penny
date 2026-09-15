import React from "react";
import Svg, {
  Circle,
  Defs,
  LinearGradient,
  Path,
  Polygon,
  Rect,
  Stop,
} from "react-native-svg";

interface PennyLogoProps {
  size?: number;
  showTrajectory?: boolean;
}

export const PennyLogo: React.FC<PennyLogoProps> = ({
  size = 24,
  showTrajectory = true,
}) => {
  return (
    <Svg width={size} height={size} viewBox="0 0 100 100" fill="none">
      <Defs>
        <LinearGradient
          id="pennyLogoCoin"
          x1="10"
          y1="10"
          x2="90"
          y2="90"
          gradientUnits="userSpaceOnUse"
        >
          <Stop offset="0%" stopColor="#FDE68A" />
          <Stop offset="30%" stopColor="#F59E0B" />
          <Stop offset="70%" stopColor="#D97706" />
          <Stop offset="100%" stopColor="#78350F" />
        </LinearGradient>

        <LinearGradient
          id="pennyLogoTraj"
          x1="10"
          y1="80"
          x2="95"
          y2="15"
          gradientUnits="userSpaceOnUse"
        >
          <Stop offset="0%" stopColor="#D97706" stopOpacity={0.4} />
          <Stop offset="50%" stopColor="#F59E0B" />
          <Stop offset="85%" stopColor="#FDE68A" />
          <Stop offset="100%" stopColor="#FFFFFF" />
        </LinearGradient>
      </Defs>

      {/* Outer Coin Rim */}
      <Circle cx="50" cy="50" r="38" fill="url(#pennyLogoCoin)" />

      {/* Inner Dark Face */}
      <Circle cx="50" cy="50" r="34" fill="#121622" />

      {/* Inner Accent Ring */}
      <Circle
        cx="50"
        cy="50"
        r="30"
        stroke="#F59E0B"
        strokeWidth="1.2"
        strokeDasharray="2 3"
        strokeOpacity={0.6}
        fill="none"
      />

      {/* Architectural 'P' Monogram */}
      <Path
        d="M38 30 H55 C65 30 72 37 72 47 C72 57 65 64 55 64 H47 V76 H38 V30 Z"
        fill="#F59E0B"
      />
      <Path
        d="M47 38 H54 C59 38 63 41 63 47 C63 53 59 56 54 56 H47 V38 Z"
        fill="#121622"
      />

      {/* Coin Notch Ticks */}
      <Rect x="34" y="42" width="6" height="2.5" rx="1" fill="#FDE68A" />
      <Rect x="34" y="52" width="6" height="2.5" rx="1" fill="#FDE68A" />

      {/* Ascending Trajectory Vector */}
      {showTrajectory && (
        <>
          <Path
            d="M12 76 C 26 76, 38 66, 48 54 C 60 40, 76 25, 90 15"
            stroke="url(#pennyLogoTraj)"
            strokeWidth="3.5"
            strokeLinecap="round"
            fill="none"
          />
          <Polygon points="94,12 86,17 92,20" fill="#FFFFFF" />
        </>
      )}
    </Svg>
  );
};
