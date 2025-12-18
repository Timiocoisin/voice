"""会员对话框模块。"""
from modules.dialogs.vip_package_dialog import VipPackageDialog

# DiamondPackageDialog 和 PaymentQRCodeDialog 将在后续提取
# 暂时从原文件导入
from modules.vip_membership_dialog import DiamondPackageDialog, PaymentQRCodeDialog

__all__ = ['VipPackageDialog', 'DiamondPackageDialog', 'PaymentQRCodeDialog']
