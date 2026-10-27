import { useFocusEffect } from 'expo-router';
import { useCallback, useRef, useState } from 'react';
import { ActivityIndicator, Image, type LayoutChangeEvent, StyleSheet, Text, View } from 'react-native';
import Svg, { Polygon, Text as SvgText } from 'react-native-svg';

import { styles } from '@/components/ui';
import { C } from '@/constants/theme';
import { api } from '@/lib/api';
import { areaPoints } from '@/lib/cameras';
import type { CameraArea } from '@/lib/types';

const REFRESH_MS = 1000;
const AREA_COLOR = '#f59e0b';

/**
 * A camera's live picture, refreshed every second while the screen is in
 * view, with its danger areas outlined (FR-32). The frame already shows the
 * camera's own detections and fills an occupied area red; the outlines here
 * show every area, including ones switched off (dashed).
 */
export function LiveCameraView({ cameraId, areas }: { cameraId: string; areas: CameraArea[] }) {
  const [uri, setUri] = useState<string | null>(null);
  const [missing, setMissing] = useState(false);
  const [aspect, setAspect] = useState(16 / 9);
  const [size, setSize] = useState({ width: 0, height: 0 });
  const measured = useRef(false);

  useFocusEffect(
    useCallback(() => {
      let stopped = false;
      async function fetchFrame() {
        try {
          const data = await api.imageDataUri(`v1/camera-frames/latest/?camera_id=${encodeURIComponent(cameraId)}`);
          if (stopped) return;
          setUri(data);
          setMissing(false);
          // The picture's shape, once: the danger areas are fractions of it.
          if (!measured.current) {
            measured.current = true;
            Image.getSize(data, (width, height) => {
              if (!stopped && width && height) setAspect(width / height);
            });
          }
        } catch {
          if (!stopped) setMissing(true);
        }
      }
      void fetchFrame();
      const timer = setInterval(fetchFrame, REFRESH_MS);
      return () => {
        stopped = true;
        clearInterval(timer);
      };
    }, [cameraId]),
  );

  const onLayout = (e: LayoutChangeEvent) => setSize(e.nativeEvent.layout);

  if (!uri) {
    return (
      <View style={[local.frame, { aspectRatio: 16 / 9 }]}>
        {missing ? (
          <Text style={styles.faint}>No live picture: the camera has sent nothing in the last 30 s.</Text>
        ) : (
          <ActivityIndicator color={C.accent} />
        )}
      </View>
    );
  }
  return (
    <View style={{ gap: 4 }}>
      <View style={[local.frame, { aspectRatio: aspect }]} onLayout={onLayout}>
        <Image
          source={{ uri }}
          fadeDuration={0}
          resizeMode="stretch"
          accessibilityLabel={`Live view from ${cameraId}`}
          style={StyleSheet.absoluteFill}
        />
        {size.width > 0 ? (
          <Svg width={size.width} height={size.height} style={StyleSheet.absoluteFill} pointerEvents="none">
            {areas.map((a) => (
              <Polygon
                key={a.id}
                points={areaPoints(a.polygon, size.width, size.height)}
                fill={a.is_active ? 'rgba(245, 158, 11, 0.12)' : 'none'}
                stroke={a.is_active ? AREA_COLOR : C.faint}
                strokeWidth={2}
                strokeDasharray={a.is_active ? undefined : '6 6'}
              />
            ))}
            {areas.map((a) => (
              <SvgText
                key={`label-${a.id}`}
                x={a.polygon[0][0] * size.width + 4}
                y={a.polygon[0][1] * size.height + 14}
                fill={a.is_active ? AREA_COLOR : C.faint}
                fontSize={12}
                fontWeight="bold">
                {a.name}
              </SvgText>
            ))}
          </Svg>
        ) : null}
      </View>
      {missing ? <Text style={styles.faint}>The camera stopped sending; showing its last picture.</Text> : null}
    </View>
  );
}

const local = StyleSheet.create({
  frame: { width: '100%', borderRadius: 8, overflow: 'hidden', backgroundColor: '#000', alignItems: 'center', justifyContent: 'center' },
});
