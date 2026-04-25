import 'package:flutter/foundation.dart';
import 'db_helper_mobile.dart' if (dart.library.html) 'db_helper_web.dart';

abstract class DatabaseHelper {
  static DatabaseHelper? _instance;
  
  static DatabaseHelper get instance {
    _instance ??= getHelper();
    return _instance!;
  }

  Future<void> cacheAlerts(List<dynamic> alerts);
  Future<List<Map<String, dynamic>>> getCachedAlerts();
}
