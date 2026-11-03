from django.core.management.base import BaseCommand

from university.payment.models import DragonpayChannel


class Command(BaseCommand):
    help = "Creates initial university.payment.DragonpayChannel data"

    def handle(self, *args, **options):
        channels = [
            {
                "proc_id": "BOG",
                "description": "Test Bank Online",
                "addon_percentage": 2,
                "addon_fixed": 25,
            },
            {
                "proc_id": "BOGX",
                "description": "Test Bank Over-the-Counter",
                "addon_percentage": 2,
                "addon_fixed": 25,
            },
            {
                "proc_id": "711",
                "description": "7/11 Convenience Store",
                "addon_percentage": 2,
                "addon_fixed": 25,
            },
            {
                "proc_id": "AAA",
                "description": "Triple A",
                "addon_percentage": 2,
                "addon_fixed": 25,
            },
            {
                "proc_id": "AUAL",
                "description": "Alipay",
                "addon_percentage": 2,
                "addon_fixed": 25,
            },
            {
                "proc_id": "AUB",
                "description": "AUB Online/Cash Payment",
                "addon_percentage": 2,
                "addon_fixed": 25,
            },
            {
                "proc_id": "BDOA",
                "description": "Banco de Oro ATM",
                "addon_percentage": 2,
                "addon_fixed": 25,
            },
            {
                "proc_id": "BDOX",
                "description": "Banco de Oro Cash Payment",
                "addon_percentage": 2,
                "addon_fixed": 25,
            },
            {
                "proc_id": "BOC",
                "description": "Bank of Commerce Online",
                "addon_percentage": 2,
                "addon_fixed": 25,
            },
            {
                "proc_id": "BDRX",
                "description": "BDO Cash Deposit w/ Ref",
                "addon_percentage": 2,
                "addon_fixed": 25,
            },
            {
                "proc_id": "BDO",
                "description": "BDO Internet Banking",
                "addon_percentage": 2,
                "addon_fixed": 25,
            },
            {
                "proc_id": "BNRX",
                "description": "BDO Network Bank (formerly ONB) Cash Dep",
                "addon_percentage": 2,
                "addon_fixed": 25,
            },
            {
                "proc_id": "BLES",
                "description": "Billease Installments",
                "addon_percentage": 2,
                "addon_fixed": 25,
                "is_active": False,
            },
            {
                "proc_id": "BPXB",
                "description": "BPI Cash Payment",
                "addon_percentage": 2,
                "addon_fixed": 25,
            },
            {
                "proc_id": "BPIA",
                "description": "BPI Online",
                "addon_percentage": 2,
                "addon_fixed": 25,
            },
            {
                "proc_id": "CEBL",
                "description": "Cebuana Lhuillier Bills Payment",
                "addon_percentage": 2,
                "addon_fixed": 25,
            },
            {
                "proc_id": "CBXB",
                "description": "Chinabank Cash Payment",
                "addon_percentage": 2,
                "addon_fixed": 25,
            },
            {
                "proc_id": "CBCB",
                "description": "Chinabank Online Bills Payment",
                "addon_percentage": 2,
                "addon_fixed": 25,
            },
            {
                "proc_id": "CVM",
                "description": "CVM PAWNSHOP",
                "addon_percentage": 2,
                "addon_fixed": 25,
            },
            {
                "proc_id": "BITC",
                "description": "Coins.ph Wallet / Bitcoin",
                "addon_percentage": 2,
                "addon_fixed": 25,
            },
            {
                "proc_id": "CC",
                "description": "Credit Card",
                "addon_percentage": 2,
                "addon_fixed": 25,
                "is_active": False,
            },
            {
                "proc_id": "DPAY",
                "description": "Dragonpay Prepaid Credits",
                "addon_percentage": 2,
                "addon_fixed": 25,
            },
            {
                "proc_id": "EWXB",
                "description": "EastWest Online/Cash Paymen",
                "addon_percentage": 2,
                "addon_fixed": 25,
            },
            {
                "proc_id": "ECPY",
                "description": "ECPay (Pawnshops, Payment Centers)",
                "addon_percentage": 2,
                "addon_fixed": 25,
            },
            {
                "proc_id": "POSB",
                "description": "FAMILY MART (POSIBLE.NET)",
                "addon_percentage": 2,
                "addon_fixed": 25,
            },
            {
                "proc_id": "GCSH",
                "description": "GCash",
                "addon_percentage": 2,
                "addon_fixed": 25,
            },
            {
                "proc_id": "GCSB",
                "description": "GCASH BILLS PAY",
                "addon_percentage": 2,
                "addon_fixed": 25,
            },
            {
                "proc_id": "LBCX",
                "description": "Gogo Xpress (Quad X)",
                "addon_percentage": 2,
                "addon_fixed": 25,
            },
            {
                "proc_id": "GRPY",
                "description": "GrabPay",
                "addon_percentage": 2,
                "addon_fixed": 25,
            },
            {
                "proc_id": "INPY",
                "description": "INSTAPAY",
                "addon_percentage": 2,
                "addon_fixed": 25,
            },
            {
                "proc_id": "I2I",
                "description": "i2i Rural Banks",
                "addon_percentage": 2,
                "addon_fixed": 25,
            },
            {
                "proc_id": "LBPA",
                "description": "Landbank ATM Online",
                "addon_percentage": 2,
                "addon_fixed": 25,
            },
            {
                "proc_id": "LBXB",
                "description": "Landbank Cash Payment",
                "addon_percentage": 2,
                "addon_fixed": 25,
            },
            {
                "proc_id": "MLH",
                "description": "M. Lhuillier",
                "addon_percentage": 2,
                "addon_fixed": 25,
            },
            {
                "proc_id": "MAYB",
                "description": "Maybank Online Banking",
                "addon_percentage": 2,
                "addon_fixed": 25,
            },
            {
                "proc_id": "MBXB",
                "description": "Metrobank Cash Payment",
                "addon_percentage": 2,
                "addon_fixed": 25,
            },
            {
                "proc_id": "MBTC",
                "description": "Metrobank Online Banking",
                "addon_percentage": 2,
                "addon_fixed": 25,
            },
            {
                "proc_id": "MNYG",
                "description": "Moneygment",
                "addon_percentage": 2,
                "addon_fixed": 25,
                "is_active": False,
            },
            {
                "proc_id": "PLWN",
                "description": "Palawan Pawnshop",
                "addon_percentage": 2,
                "addon_fixed": 25,
            },
            {
                "proc_id": "PYMB",
                "description": "PayMaya Bills Pay",
                "addon_percentage": 2,
                "addon_fixed": 25,
            },
            {
                "proc_id": "PYMY",
                "description": "PayMaya",
                "addon_percentage": 2,
                "addon_fixed": 25,
            },
            {
                "proc_id": "PYPL",
                "description": "PayPal",
                "addon_percentage": 2,
                "addon_fixed": 25,
                "is_active": False,
            },
            {
                "proc_id": "PRHB",
                "description": "PERAHUB",
                "addon_percentage": 2,
                "addon_fixed": 25,
            },
            {
                "proc_id": "PSNT",
                "description": "PESONET",
                "addon_percentage": 2,
                "addon_fixed": 25,
            },
            {
                "proc_id": "POSB",
                "description": "PHOENIX GAS STATION (POSIBLE.NET)",
                "addon_percentage": 2,
                "addon_fixed": 25,
            },
            {
                "proc_id": "PNXB",
                "description": "PNB Cash Payment",
                "addon_percentage": 2,
                "addon_fixed": 25,
            },
            {
                "proc_id": "PNBB",
                "description": "PNB Internet Banking Bills Payment",
                "addon_percentage": 2,
                "addon_fixed": 25,
            },
            {
                "proc_id": "PNBR",
                "description": "PNB Remittance (selective)",
                "addon_percentage": 2,
                "addon_fixed": 25,
            },
            {
                "proc_id": "PSB",
                "description": "PSBank Online",
                "addon_percentage": 2,
                "addon_fixed": 25,
            },
            {
                "proc_id": "POSB",
                "description": "POSSIBLE.NET",
                "addon_percentage": 2,
                "addon_fixed": 25,
            },
            {
                "proc_id": "RCXB",
                "description": "RCBC Cash Payment / ATM Bills Payment",
                "addon_percentage": 2,
                "addon_fixed": 25,
            },
            {
                "proc_id": "RCBC",
                "description": "RCBC Online Banking",
                "addon_percentage": 2,
                "addon_fixed": 25,
            },
            {
                "proc_id": "RDP",
                "description": "RD Pawnshop",
                "addon_percentage": 2,
                "addon_fixed": 25,
            },
            {
                "proc_id": "RDS",
                "description": "Robinsons Dept Store",
                "addon_percentage": 2,
                "addon_fixed": 25,
            },
            {
                "proc_id": "RSBB",
                "description": "RobinsonsBank Cash Payment",
                "addon_percentage": 2,
                "addon_fixed": 25,
            },
            {
                "proc_id": "RSB",
                "description": "RobinsonsBank Online Bills Payment",
                "addon_percentage": 2,
                "addon_fixed": 25,
            },
            {
                "proc_id": "RLNT",
                "description": "RuralNet Banks and Coops",
                "addon_percentage": 2,
                "addon_fixed": 25,
            },
            {
                "proc_id": "SBCB",
                "description": "Security Bank Cash Payment",
                "addon_percentage": 2,
                "addon_fixed": 25,
            },
            {
                "proc_id": "SPAY",
                "description": "Shopeepay",
                "addon_percentage": 2,
                "addon_fixed": 25,
            },
            {
                "proc_id": "SMR",
                "description": "SM Dept/Supermarket/Savemore Counter",
                "addon_percentage": 2,
                "addon_fixed": 25,
            },
            {
                "proc_id": "TAYO",
                "description": "TAYO CASH",
                "addon_percentage": 2,
                "addon_fixed": 25,
            },
            {
                "proc_id": "TNDO",
                "description": "Tendopay Installments",
                "addon_percentage": 2,
                "addon_fixed": 25,
                "is_active": False,
            },
            {
                "proc_id": "UCXB",
                "description": "UCPB ATM/Cash Payment",
                "addon_percentage": 2,
                "addon_fixed": 25,
            },
            {
                "proc_id": "UCPB",
                "description": "UCPB Connect/Mobile",
                "addon_percentage": 2,
                "addon_fixed": 25,
            },
            {
                "proc_id": "UBXB",
                "description": "Unionbank Cash Payment",
                "addon_percentage": 2,
                "addon_fixed": 25,
            },
            {
                "proc_id": "UBPB",
                "description": "Unionbank Internet Banking",
                "addon_percentage": 2,
                "addon_fixed": 25,
            },
            {
                "proc_id": "USSC",
                "description": "USSC",
                "addon_percentage": 2,
                "addon_fixed": 25,
            },
            {
                "proc_id": "AUWC",
                "description": "WeChat Pay",
                "addon_percentage": 2,
                "addon_fixed": 25,
            },
            {
                "proc_id": "XNPY",
                "description": "XANPAY (HK,SG,TH,MY and AU)",
                "addon_percentage": 2,
                "addon_fixed": 25,
            },
        ]

        for channel in channels:
            proc_id = channel.pop("proc_id")
            description = channel.pop("description")

            DragonpayChannel.objects.update_or_create(
                proc_id=proc_id, description=description, defaults=channel
            )
