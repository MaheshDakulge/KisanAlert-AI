import 'dart:convert';
import 'package:http/http.dart' as http;
class AuthService {
  static const String _baseUrl = 'https://kisanalert-api-862035785988.asia-south1.run.app/api/v1/auth';

  static Future<String?> login(String phone, String name) async {
    try {
      final res = await http.post(
        Uri.parse('$_baseUrl/login'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'phone_number': phone,
          'name': name,
          'district': 'Nanded',
          'language': 'mr',
          'fcm_token': ''
        }),
      );
      if (res.statusCode == 200) {
        final data = jsonDecode(res.body);
        return data['farmer_id'] as String?;
      }
    } catch (e) {
      print('Auth error: $e');
    }
    return null;
  }

  static Future<bool> savePreferences(String farmerId, String crop, bool wa, bool sms, bool voice) async {
    try {
      final res = await http.post(
        Uri.parse('$_baseUrl/preferences'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'farmer_id': farmerId,
          'crop_name': crop,
          'alert_whatsapp': wa,
          'alert_sms': sms,
          'alert_voice': voice,
        }),
      );
      return res.statusCode == 200;
    } catch (e) {
      print('Pref error: $e');
      return false;
    }
  }
}
