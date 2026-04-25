import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart';
import 'package:path_provider/path_provider.dart';
import 'dart:io';
import 'db_helper.dart';

DatabaseHelper getHelper() => DatabaseHelperMobile();

class DatabaseHelperMobile implements DatabaseHelper {
  static Database? _database;

  Future<Database> get database async {
    if (_database != null) return _database!;
    _database = await _initDb();
    return _database!;
  }

  Future<Database> _initDb() async {
    Directory documentsDirectory = await getApplicationDocumentsDirectory();
    String path = join(documentsDirectory.path, 'kisanalert.db');

    return await openDatabase(
      path,
      version: 1,
      onCreate: (db, version) async {
        await db.execute('''
          CREATE TABLE alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            commodity TEXT,
            district TEXT,
            price REAL,
            crash_score REAL,
            alert_level TEXT,
            message TEXT,
            created_at TEXT
          )
        ''');
      },
    );
  }

  @override
  Future<void> cacheAlerts(List<dynamic> alerts) async {
    final db = await database;
    await db.transaction((txn) async {
      await txn.delete('alerts');
      for (var alert in alerts) {
        await txn.insert('alerts', {
          'commodity': alert['commodity'],
          'district': alert['district'],
          'price': alert['price'],
          'crash_score': alert['crash_score'],
          'alert_level': alert['alert_level'],
          'message': alert['message'],
          'created_at': alert['created_at'],
        });
      }
    });
  }

  @override
  Future<List<Map<String, dynamic>>> getCachedAlerts() async {
    final db = await database;
    return await db.query('alerts', orderBy: 'created_at DESC');
  }
}
