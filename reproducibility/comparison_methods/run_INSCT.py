from tnn.tnn import *
from ivis import Ivis
import scanpy as sc
import pandas as pd
import anndata as ad
from time import time
#os.environ["CUDA_VISIBLE_DEVICES"]="1"
from memory_profiler import memory_usage


def my_func(adata):
    sc.pp.filter_genes(adata, min_cells=3)
    sc.pp.filter_cells(adata, min_genes=200)

    sc.pp.normalize_total(adata, target_sum=1e4)
    sc.pp.log1p(adata)
    sc.pp.highly_variable_genes(adata, n_top_genes=1000, flavor='seurat')
    highly_variable = adata.var['highly_variable']
    adata = adata[:, adata.var['highly_variable']]
    sc.tl.pca(adata, n_comps=50)

    model = TNN(k=20, embedding_dims=2, batch_size=64, n_epochs_without_progress=10, verbose=0,
                epochs=200, k_to_m_ratio=0.75,approx=False)
    model.fit(X=adata, batch_name="batch", shuffle_mode=True)
    adata.obsm['X_tnn'] = model.transform(adata)

    #sc.pp.neighbors(adata, use_rep="X_insct")
    #sc.tl.umap(adata)

    return adata


#asw_deepMNN = silhouette_coeff_ASW(adata_result)
#entropy_deepMNN=compute_entropy(adata_result)
#adata_result.obs['batch'] = ['10X 3\'' if i == '0' else '10X 5\'' for i in adata_result.obs['batch']]
#sc.pl.umap(adata_result,color=['batch','celltype'],save='_figure3_deepMNN_batch.pdf')
for dataset in ['mouse_pancreas', 'mouse_atlas','human_pancreas','human_pancreas_2','human_lung','human_heart','mouse_brain']:

    print('----------------data: {} ----------------- '.format(dataset))

    if dataset == 'mouse_pancreas':
        csv_data = pd.read_csv('../../datasets/mouse_pancreas/GSM2230761_mouse1_umifm_counts.csv')
        barcode = csv_data['barcode'].values
        assigned_cluster = csv_data['assigned_cluster'].values
        gene_expression = csv_data.iloc[:, 3:].values
        adata1 = ad.AnnData(X=gene_expression, obs={'barcode': barcode, 'celltype': assigned_cluster})
        csv_data = pd.read_csv('../../datasets/mouse_pancreas/GSM2230762_mouse2_umifm_counts.csv')
        barcode = csv_data['barcode'].values
        assigned_cluster = csv_data['assigned_cluster'].values
        gene_expression = csv_data.iloc[:, 3:].values
        adata2 = ad.AnnData(X=gene_expression, obs={'barcode': barcode, 'celltype': assigned_cluster})
        adata = [adata1, adata2]
        adata = ad.concat(adata, merge="same")
        adata.obs['batch'] = np.concatenate((np.array(['batch1'] * adata1.n_obs), np.array(['batch2'] * adata2.n_obs)), axis=0)
        adata.var_names = csv_data.columns[3:]
        batch_name = np.array(['batch1', 'batch2'], dtype=object)

    elif dataset == 'mouse_atlas':
        adata1 = ad.read_h5ad('../../datasets/mouse_atlas/rna_seq_mi.h5ad')
        adata2 = ad.read_h5ad('../../datasets/mouse_atlas/rna_seq_sm.h5ad')
        adata = [adata1, adata2]
        adata = ad.concat(adata, merge="same")
        adata.obs['batch'] = np.concatenate((np.array(['batch1']*adata1.n_obs), np.array(['batch2']*adata2.n_obs)), axis=0)
        batch_name = np.array(['batch1', 'batch2'], dtype=object)

    elif dataset == 'mouse_brain':
        adata = sc.read_h5ad("../../datasets/mouse_brain/sub_mouse_brain.h5ad")
        adata.obs.rename(columns={'BATCH': 'batch'}, inplace=True)
        adata1 = adata[adata.obs['batch'].values == 'batch1']
        adata2 = adata[adata.obs['batch'].values == 'batch2']
        adata = ad.concat([adata1, adata2], merge='same')
        batch_name = np.array(['batch1', 'batch2'], dtype=object)

    elif dataset == 'human_pancreas_2':
        adata1 = ad.read_h5ad('./datasets/human_pancreas_2/rna_seq_baron.h5ad')
        adata2 = ad.read_h5ad('./datasets/human_pancreas_2/rna_seq_segerstolpe.h5ad')
        adata = [adata1, adata2]
        adata = ad.concat(adata, merge="same")
        adata.obs.rename(columns={'cell_type1': 'celltype'}, inplace=True)
        adata.obs['batch'] = np.concatenate((np.array(['batch1']*adata1.n_obs), np.array(['batch2']*adata2.n_obs)), axis=0)
        batch_name = np.array(['batch1', 'batch2'], dtype=object)

    elif dataset == 'human_pancreas':
        adata = sc.read("../../datasets/human_pancreas/human_pancreas.h5ad")
        batch_name = np.array(['human1', 'human2', 'human3', 'human4'], dtype=object)

    elif dataset == 'human_lung':
        adata = sc.read_h5ad("../../datasets/human_lung/human_lung_marker.h5ad")
        adata.obs['batch'].replace('muc3843', 'batch1', inplace=True)
        adata.obs['batch'].replace('muc4658', 'batch2', inplace=True)
        adata.obs['batch'].replace('muc5103', 'batch3', inplace=True)
        adata.obs['batch'].replace('muc5104', 'batch4', inplace=True)
        batch_name = np.array(['batch1', 'batch2', 'batch3', 'batch4'], dtype=object)


    elif dataset == 'human_heart':
        adata = sc.read("../../datasets/human_heart/healthy_human_heart.h5ad")
        adata.obs.rename(columns={'sampleID': 'batch'}, inplace=True)
        unique_sampleIDs = adata.obs['batch'].values.unique()[-10:]
        adata = adata[adata.obs['batch'].isin(unique_sampleIDs)]
        batch_name = unique_sampleIDs
        for i in range(len(batch_name)):
            adata.obs['batch'].replace(batch_name[i], 'batch'+str(i+1), inplace=True)
        batch_name=np.array(['batch1', 'batch2', 'batch3','batch4','batch5','batch6','batch7','batch8','batch9','batch10'])


    start = time()
    adata = my_func(adata)
    corrd = pd.DataFrame(adata.obsm['X_tnn'])
    adata_corrd = ad.AnnData(corrd, obs=adata.obs, dtype='float64')
    adata_corrd.obsm['X_latent'] = adata.obsm['X_tnn']
    adata_corrd.obs['celltype'] = np.array(adata.obs['celltype'])
    adata_corrd.obs['batch'] = np.array(adata.obs['batch'])

    mem_used = memory_usage(-1, interval=.1, timeout=1)
    print("elapsed memory:", max(mem_used))
    end = time()
    print('elapsed{:.2f} seconds'.format(end - start))

    sc.pp.neighbors(adata_corrd,use_rep="X_latent")
    sc.tl.louvain(adata_corrd, resolution=0.5)

    adata_corrd.write_h5ad("INSCT_"+dataset + ".h5ad")
