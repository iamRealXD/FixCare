import 'package:flutter_test/flutter_test.dart';
import 'package:fixcare/core/utils/extensions.dart';

void main() {
  group('StringExtensions', () {
    test('capitalize capitalizes first letter', () {
      expect('hello'.capitalize(), 'Hello');
      expect('WORLD'.capitalize(), 'World');
      expect(''.capitalize(), '');
    });

    test('capitalizeWords capitalizes each word', () {
      expect('hello world'.capitalizeWords(), 'Hello World');
      expect('fixcare app'.capitalizeWords(), 'Fixcare App');
    });

    test('isNotBlank checks for non-empty trimmed string', () {
      expect('hello'.isNotBlank, true);
      expect('  '.isNotBlank, false);
      expect(''.isNotBlank, false);
    });
  });

  group('DateTimeExtensions', () {
    test('formatRelative formats recent times', () {
      final now = DateTime.now();
      expect(now.formatRelative(), 'Just now');
    });
  });
}