from dataclasses import dataclass, field
from typing import List


@dataclass
class OperatorData:
    operator_id: int
    server_id: int
    operator_name: str
    operator_name_link: str
    currencies: List[str]


OPERATOR_DATA_SET: List[OperatorData] = [
    OperatorData(8000000, 5555, "DefaultMinQuickfire", "MinQuickFire", ["GBP", "MYR", "ZAR", "ZMW", "PHP", "JPY", "CLP"]),
    OperatorData(8000001, 5556, "IslandParadise_Default_1_Bet", "Default1BetQuickFire", ["GBP"]),
    OperatorData(8001099, 5570, "NewMaxbetof2", "NewMaxbetof2", ["GBP"]),
    OperatorData(8000005, 5567, "NewMaxbetof5", "NewMaxbetof5", ["GBP"]),
    OperatorData(8000010, 5568, "NewMaxbetof10", "NewMaxbetof10", ["GBP"]),
    OperatorData(8000020, 5569, "NewMaxbetof20", "NewMaxbetof20", ["GBP"]),
    OperatorData(8000002, 5557, "IslandParadise_Default_2_Bet", "Default2BetQuickFire", ["GBP"]),
    OperatorData(8000031, 5558, "Germany Quickfire", "GermanyQuickFire", ["EUR"]),
    OperatorData(8000037, 5559, "Greece140K", "Greece140K", ["EUR"]),
    OperatorData(8000050, 5560, "50KMaxBet", "50KMaxBet", ["GBP"]),
    OperatorData(8000100, 5561, "100KMaxBet", "100KMaxBet", ["GBP"]),
    OperatorData(8000150, 5562, "150KMaxBet", "150KMaxBet", ["GBP"]),
    OperatorData(8050000, 5549, "50KMaxExposure", "50KMEQuickfire", ["GBP", "MYR", "ZAR", "ZMW", "PHP", "JPY", "CLP"]),
    OperatorData(8100000, 5550, "100KMaxExposure", "100KMaxExposure", ["GBP", "MYR", "ZAR", "ZMW", "PHP", "JPY", "CLP"]),
    OperatorData(8125000, 5551, "125KMaxExposure", "125KMaxExposure", ["GBP", "MYR", "ZAR", "ZMW", "PHP", "JPY", "CLP"]),
    OperatorData(8250000, 5552, "250KMaxExposure", "250KMaxExposure", ["GBP", "MYR", "ZAR", "ZMW", "PHP", "JPY", "CLP"]),
    OperatorData(8500000, 5553, "500KMaxExposure", "500KMaxExposure", ["GBP", "MYR", "ZAR", "ZMW", "PHP", "JPY", "CLP"]),
    OperatorData(8750000, 5554, "750KMaxExposure", "750KMaxExposure", ["GBP", "MYR", "ZAR", "ZMW", "PHP", "JPY", "CLP"]),
    OperatorData(8111000, 5602, "1MillionMaxExposure", "1MillionMaxExposure", ["USD"]),
    OperatorData(8112000, 5603, "2MillionMaxExposure", "2MillionMaxExposure", ["USD"]),
    OperatorData(8113000, 5604, "3MillionMaxExposure", "3MillionMaxExposure", ["USD"]),
    OperatorData(8115000, 5605, "5MillionMaxExposure", "5MillionMaxExposure", ["USD"]),
    OperatorData(8110000, 5606, "10MillionMaxExposure", "10MillionMaxExposure", ["USD"]),
    OperatorData(8000006, 5581, "Default200MaxExposure250k", "Default200MaxExposure250k", ["USD"]),
    OperatorData(8000007, 5582, "Default200MaxExposure500k", "Default200MaxExposure500k", ["USD"]),
    OperatorData(8000008, 5583, "Default200MaxExposure750k", "Default200MaxExposure750k", ["USD"]),
]
