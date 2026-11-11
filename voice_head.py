"""Small trainable classifier over a fully frozen acoustic encoder and AASIST pool."""
import torch
def make_head(dim=160):
 return torch.nn.Sequential(torch.nn.LayerNorm(dim),torch.nn.Linear(dim,64),torch.nn.GELU(),torch.nn.Linear(64,1))
