import pandas as pd
import pickle
from sklearn.metrics import mean_absolute_error
from sklearn.metrics import median_absolute_error
from sklearn.metrics import mean_absolute_percentage_error
from sklearn.model_selection import StratifiedKFold

from utils.data_loading import get_my_data
from utils.stratification import stratify_y
from train_model import tune_and_fit

from sklearn.model_selection import RepeatedKFold
from collections import namedtuple

# Parameters
features_list = ["fingerprints", "descriptors", "all"]
SMOKE = False
################

if SMOKE:
    print("Running smoke test...")
    amount_of_data = 2000
    number_of_folds = 2
    number_of_trials = 1
    param_search_folds = 2
    database = "sqlite:///./results/smokeDatabaseYouCanDeleteMe.db"
else:
    amount_of_data = "All"
    number_of_folds = 5
    number_of_trials = 100
    param_search_folds = 5
    database = "sqlite:///./results/cv.db"


if __name__=="__main__":
    # Load data
    print("Loading data")
    X, y, desc_cols, fgp_cols = get_my_data(common_cols=['unique_id', 'correct_ccs_avg'])
    if amount_of_data != "All":
        X = X[:amount_of_data]
        y = y[:amount_of_data]

    results = []

    ParamSearchConfig = namedtuple('ParamSearchConfig', ['storage', 'study_prefix', 'param_search_cv', 'n_trials'])
    param_search_config = ParamSearchConfig(
            storage=database,
            study_prefix="blender",
            param_search_cv=RepeatedKFold(n_splits=param_search_folds, n_repeats=1, random_state=42),
            n_trials=number_of_trials
    )
    cross_validation = StratifiedKFold(n_splits=number_of_folds, shuffle=True, random_state=42)

    for fold, (train_index, test_index) in enumerate(cross_validation.split(X, stratify_y(y))):
        param_search_config = param_search_config._replace(
            study_prefix=f"cv-fold-{fold}"
        )
        train_split_X = X[train_index]
        train_split_y = y[train_index]
        test_split_X = X[test_index]
        test_split_y = y[test_index]

        # TODO: blender_Config
        preprocessor, blender = (
            tune_and_fit(train_split_X, train_split_y, desc_cols, fgp_cols,
                         param_search_config=param_search_config, blender_config=blender_config)
        )

        print("Saving preprocessor and BLENDEr")
        with open(f"./results/blender-preprocessor-{features}-{fold}.pkl", "wb") as f:
            pickle.dump(preprocessor, f)
        with open(f"./results/blender-{fold}.pkl", "wb") as f:
            pickle.dump(blender, f)

        X_test = preprocessor.transform(test_split_X)
        results.append(
            evaluate_all_estimators(blender, test_split_X, test_split_y, metrics, fold)
        )
        # Save all intermediate results
        print(f"Saving intermediate results:")
        intermediate_results = pd.concat(results, axis=0)
        intermediate_results.to_csv(f"./results/blender_partial_results{len(results)}.txt", index=False)

    # Print and save final results
    results = pd.concat(results, axis=0)
    print(f"Saving final results")
    print(results)
    results.to_csv(f"./results/blender_cross_validation_results.txt", index=False)

