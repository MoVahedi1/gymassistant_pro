import 'package:get/get.dart';
import 'package:gymassistant_pro/core/services/auth_service.dart';
import 'package:gymassistant_pro/core/services/local_db_service.dart';
import 'package:gymassistant_pro/core/services/sync_service.dart';

class AuthController extends GetxController {
  final AuthService authService = Get.find();
  final LocalDbService localDb = Get.find();
  final SyncService syncService = Get.find();

  final RxBool isLoading = false.obs;
  final RxBool isVerificationSent = false.obs;
  final phoneController = TextEditingController();
  final verificationCodeController = TextEditingController();
  final nameController = TextEditingController();

  Future<void> sendVerificationCode() async {
    if (phoneController.text.isEmpty) {
      Get.snackbar('خطا', 'لطفا شماره موبایل را وارد کنید');
      return;
    }

    isLoading.value = true;
    try {
      await authService.sendVerificationCode(phoneController.text);
      isVerificationSent.value = true;
      Get.snackbar('موفق', 'کد تایید ارسال شد');
    } catch (e) {
      Get.snackbar('خطا', 'ارسال کد ناموفق بود');
    } finally {
      isLoading.value = false;
    }
  }

  Future<void> verifyCode() async {
    if (verificationCodeController.text.isEmpty) {
      Get.snackbar('خطا', 'لطفا کد تایید را وارد کنید');
      return;
    }

    isLoading.value = true;
    try {
      final user = await authService.verifyCode(
        phoneController.text,
        verificationCodeController.text,
        nameController.text.isEmpty ? 'کاربر' : nameController.text,
      );
      
      await localDb.saveUser(user);
      
      if (user.status == UserStatus.approved) {
        Get.offAllNamed('/home');
        await syncService.syncAllData();
      } else {
        Get.offAllNamed('/pending-approval');
      }
    } catch (e) {
      Get.snackbar('خطا', 'تایید کد ناموفق بود');
    } finally {
      isLoading.value = false;
    }
  }

  Future<void> logout() async {
    await authService.logout();
    await localDb.userBox.clear();
    Get.offAllNamed('/login');
  }

  @override
  void onClose() {
    phoneController.dispose();
    verificationCodeController.dispose();
    nameController.dispose();
    super.onClose();
  }
}