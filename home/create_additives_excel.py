import pandas as pd

data = {
    "name": ["Ferrocene", "MMT"],
    "cost_usd_per_litre": [2.5, 8.5],
    "density_add": [1.05, 1.05],
}
df = pd.DataFrame(data)
df.to_excel("home/ubuntu/fuel_blending/data_examples/additives_example.xlsx", index=False)
print("Additives Excel file with Ferrocene and MMT created.") 