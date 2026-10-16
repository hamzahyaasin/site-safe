import { ActivityIndicator, Pressable, StyleSheet, Text, TextInput, TextInputProps, View, ViewProps } from 'react-native';

import { C } from '@/constants/theme';

export function Screen({ style, ...props }: ViewProps) {
  return <View style={[styles.screen, style]} {...props} />;
}

export function Card({ style, ...props }: ViewProps) {
  return <View style={[styles.card, style]} {...props} />;
}

export function Badge({ label, color }: { label: string; color: string }) {
  return (
    <View style={[styles.badge, { borderColor: color, backgroundColor: `${color}22` }]}>
      <Text style={[styles.badgeText, { color }]}>{label}</Text>
    </View>
  );
}

export function Button({
  title,
  onPress,
  disabled,
  busy,
  tone = 'primary',
}: {
  title: string;
  onPress: () => void;
  disabled?: boolean;
  busy?: boolean;
  tone?: 'primary' | 'secondary' | 'danger';
}) {
  const bg = tone === 'primary' ? C.accent : tone === 'danger' ? C.bad : 'transparent';
  return (
    <Pressable
      accessibilityRole="button"
      onPress={onPress}
      disabled={disabled || busy}
      style={({ pressed }) => [
        styles.button,
        { backgroundColor: bg, borderColor: tone === 'secondary' ? C.border : bg },
        (pressed || disabled) && { opacity: 0.6 },
      ]}>
      {busy ? (
        <ActivityIndicator color={tone === 'secondary' ? C.text : '#000'} />
      ) : (
        <Text style={[styles.buttonText, { color: tone === 'secondary' ? C.text : '#111' }]}>{title}</Text>
      )}
    </Pressable>
  );
}

export function Field({ label, ...props }: TextInputProps & { label: string }) {
  return (
    <View style={{ gap: 6 }}>
      <Text style={styles.label}>{label}</Text>
      <TextInput placeholderTextColor={C.faint} style={styles.input} accessibilityLabel={label} {...props} />
    </View>
  );
}

export function Empty({ title, detail }: { title: string; detail?: string }) {
  return (
    <View style={styles.empty}>
      <Text style={styles.emptyTitle}>{title}</Text>
      {detail ? <Text style={styles.muted}>{detail}</Text> : null}
    </View>
  );
}

export function ErrorText({ children }: { children: string }) {
  return (
    <Text accessibilityRole="alert" style={styles.error}>
      {children}
    </Text>
  );
}

export const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: C.bg },
  card: { backgroundColor: C.card, borderColor: C.border, borderWidth: 1, borderRadius: 10, padding: 14 },
  badge: { borderWidth: 1, borderRadius: 6, paddingHorizontal: 7, paddingVertical: 2, alignSelf: 'flex-start' },
  badgeText: { fontSize: 11, fontWeight: '700' },
  button: { minHeight: 46, borderRadius: 8, borderWidth: 1, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 16 },
  buttonText: { fontSize: 15, fontWeight: '700' },
  label: { color: C.muted, fontSize: 13, fontWeight: '600' },
  input: { minHeight: 46, borderRadius: 8, borderWidth: 1, borderColor: C.border, backgroundColor: '#0b0d12', color: C.text, paddingHorizontal: 12, fontSize: 15 },
  title: { color: C.text, fontSize: 16, fontWeight: '700' },
  text: { color: C.text, fontSize: 14 },
  muted: { color: C.muted, fontSize: 13 },
  faint: { color: C.faint, fontSize: 12 },
  empty: { alignItems: 'center', padding: 40, gap: 6 },
  emptyTitle: { color: C.text, fontSize: 15, fontWeight: '600' },
  error: { color: '#fca5a5', backgroundColor: '#ef444422', borderColor: '#ef444466', borderWidth: 1, borderRadius: 8, padding: 10, fontSize: 13 },
});
