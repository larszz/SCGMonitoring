class ShippingConfig:
    target: str
    shipping_method: str
    order_point: int
    quantity: int
    priority: int

    def short_summary_only_values(self):
        return f"SM:\t{self.shipping_method}\nOP:\t{self.order_point}\nQ:\t{self.quantity}\nPR:\t{self.priority}"


class FactoryData:
    name: str = 1
    capacity: int
    capacity_modifications: list
    shipping_configs: list[ShippingConfig]

    def __init__(self):
        self.name = ''
        self.capacity = 0.0
        self.capacity_modifications = []
        self.shipping_configs = []


