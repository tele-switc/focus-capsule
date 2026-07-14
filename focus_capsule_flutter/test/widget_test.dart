import 'package:flutter_test/flutter_test.dart';
import 'package:focus_capsule_flutter/main.dart';

void main() {
  testWidgets('Focus Capsule smoke test', (WidgetTester tester) async {
    await tester.pumpWidget(const FocusCapsuleApp());
    expect(find.text('专注神器'), findsOneWidget);
  });
}
