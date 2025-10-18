import pandas as pd
import os

#input and output setup
input_file = r"" #path to file 
output_dir = r"" #path to file 
os.makedirs(output_dir, exist_ok=True)

#read the full CSV
df = pd.read_csv(input_file)

#shuffle the dataset once using a fixed seed (ensures reproducibility)
df_shuffled = df.sample(frac=1, random_state=42).reset_index(drop=True)

#split the shuffled data into 20 parts of 100 rows each
chunk_size = 100
num_chunks = 20

for i in range(num_chunks):
    start = i * chunk_size
    end = start + chunk_size
    chunk_df = df_shuffled.iloc[start:end]
    output_file = os.path.join(output_dir, f"NESO_sample_{i+1:02d}.csv")
    chunk_df.to_csv(output_file, index=False)
    print(f"Wrote {output_file} ({len(chunk_df)} rows)")