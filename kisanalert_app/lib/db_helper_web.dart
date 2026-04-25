import 'db_helper.dart';

DatabaseHelper getHelper() => DatabaseHelperWeb();

class DatabaseHelperWeb implements DatabaseHelper {
  @override
  Future<void> cacheAlerts(List<dynamic> alerts) async {
    // Web par caching bypass kar rahe hain (ya SharedPrefs use kar sakte hain)
    return;
  }

  @override
  Future<List<Map<String, dynamic>>> getCachedAlerts() async {
    return [];
  }
}
