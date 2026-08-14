import 'package:flutter_test/flutter_test.dart';
import 'package:fixcare/main.dart';

void main() {
  testWidgets('App loads without crashing', (WidgetTester tester) async {
    await tester.pumpWidget(const FixCareApp());
    await tester.pumpAndSettle();
    
    // Verify the app renders
    expect(find.byType(MaterialApp), findsOneWidget);
  });
}