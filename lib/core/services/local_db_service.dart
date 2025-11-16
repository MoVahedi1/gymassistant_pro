import 'package:get/get.dart';
import 'package:hive/hive.dart';

class LocalDbService extends GetxService {
  late Box userBox;

  Future<LocalDbService> init() async {
    Hive.init((await getApplicationDocumentsDirectory()).path);
    userBox = await Hive.openBox('users');
    return this;
  }
}
