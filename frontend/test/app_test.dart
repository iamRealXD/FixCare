import 'package:flutter_test/flutter_test.dart';
import 'package:flutter/material.dart';
import 'package:fixcare/app/app.dart';

void main() {
  testWidgets('App loads without crashing', (WidgetTester tester) async {
    await tester.pumpWidget(const FixCareApp());
    await tester.pump(const Duration(milliseconds: 500));
    
    // Verify the app renders
    expect(find.byType(MaterialApp), findsOneWidget);
  });
}