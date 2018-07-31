### (Scikit) Model Helpers ###
### Peter Lillian & Lucas Hu ###

# Imports
import numpy as np
from sklearn.model_selection import StratifiedKFold
from sklearn.model_selection import GridSearchCV, RandomizedSearchCV, train_test_split
from sklearn.metrics import make_scorer, fbeta_score, confusion_matrix, roc_curve, auc
from scipy import interp
import matplotlib.pyplot as plt

# Threshold y_prob at 'threshold' --> binary array
def apply_threshold(y_prob, threshold=0.5):
	y_pred = np.array(y_prob >= threshold).astype(np.int32) # thresholding
	return y_pred

# Compute TN, FP, FN, TP
def compute_confusion(y_pred, y_test):
	confusion = confusion_matrix(y_test, y_pred) # calculate confusion matrix
	return confusion.flatten().tolist()

# Explain TN, FP, FN, TP
	# Stats = (TN, FP, FN, TP) OR (TN, FP, FN, TP, fc_indeterminate, kd_indeterminate)
def explain_confusion(stats, indeterminates=False):
	if indeterminates == False:
		fc_total = stats[0] + stats[1]
		kd_total = stats[2] + stats[3]
		fc_as_fc = (stats[0] / fc_total) * 100
		print("FC Classified as FC: " + str(stats[0]) + ", (" + str(fc_as_fc) + " %)")
		fc_as_kd = (stats[1] / fc_total) * 100
		print("FC Classified as KD: " + str(stats[1]) + ", (" + str(fc_as_kd) + " %)")
		kd_as_fc = (stats[2] / kd_total) * 100
		print("KD Classified as FC: " + str(stats[2]) + ", (" + str(kd_as_fc) + " %)")
		kd_as_kd = (stats[3] / kd_total) * 100
		print("KD Classified as KD: " + str(stats[3]) + ", (" + str(kd_as_kd) + " %)")
		print("Avg sensitivity: " + str(stats[3]/(stats[3]+stats[2]))) # TP/(TP+FN)
		print("Avg specificity: " + str(stats[0]/(stats[0]+stats[1]))) # TN/(TN+FP)
	else:
		fc_indeterminate = stats[4]
		kd_indeterminate = stats[5]
		fc_total = stats[0] + stats[1] + fc_indeterminate
		kd_total = stats[2] + stats[3] + kd_indeterminate
		fc_as_fc = (stats[0] / fc_total) * 100
		print("FC Classified as FC: " + str(stats[0]) + ", (" + str(fc_as_fc) + " %)")
		fc_as_kd = (stats[1] / fc_total) * 100
		print("FC Classified as KD: " + str(stats[1]) + ", (" + str(fc_as_kd) + " %)")
		kd_as_fc = (stats[2] / kd_total) * 100
		print("KD Classified as FC: " + str(stats[2]) + ", (" + str(kd_as_fc) + " %)")
		kd_as_kd = (stats[3] / kd_total) * 100
		print("KD Classified as KD: " + str(stats[3]) + ", (" + str(kd_as_kd) + " %)")
		pct_fc_indeterminate = (fc_indeterminate/fc_total) * 100
		print("FC left indeterminate: " + str(fc_indeterminate) + ", (" + str(pct_fc_indeterminate) + " %)")
		pct_kd_indeterminate = (kd_indeterminate/kd_total) * 100
		print("KD left indeterminate: " + str(kd_indeterminate) + ", (" + str(pct_kd_indeterminate) + " %)")
		print("Avg sensitivity: " + str(stats[3]/(stats[3]+stats[2]))) # TP/(TP+FN)
		print("Avg specificity: " + str(stats[0]/(stats[0]+stats[1]))) # TN/(TN+FP)

# Return thresholds corresponding to PPV >= 0.95 (predict KD) and NPV >= 0.95 (predict FC)
	# y_prob: predicted probabilities from trained model
	# y_test: actual y labels
	# threshold_step: granularity with which to test out various classification thresholds
	# pv_threshold: PPV/NPV target for thresholds (default 0.95)
	# Returns (fc_threshold, kd_threshold).
		# If predicted score < fc_threshold, then predict FC
		# If predicted score > kd_threshold, then predict KD
		# If predicted score b/w (fc_threshold, kd_threshold), then indeterminate
def get_fc_kd_thresholds(y_prob, y_test, threshold_step=0.001, pv_threshold=0.95):
	thresholds = np.arange(0.0, 1.0, step=threshold_step) # which thresholds to try
	valid_thresholds_ppv = [] # thresholds where PPV >= 0.95
	valid_thresholds_npv = [] # thresholds where NPV >= 0.95
	
	for threshold in thresholds: # Iterate over possible thresholds (TODO: binary search?)
		y_pred = apply_threshold(y_prob, threshold)
		tn, fp, fn, tp = compute_confusion(y_pred, y_test)
		try: ppv = tp / (tp + fp) # PPV: positive predictive value
		except: ppv = -1
		try: npv = tn / (tn + fn) # NPV: negative predictive value
		except: npv = -1
		if ppv >= pv_threshold: 
			valid_thresholds_ppv.append(threshold)
		if npv >= pv_threshold:
			valid_thresholds_npv.append(threshold)
	# print(np.column_stack((y_prob, y_test)))
	try: 
		kd_threshold = min(valid_thresholds_ppv) # lowest threshold past which PPV >= 0.95 (predict KD)
	except: 
		kd_threshold = 0.0
		print('WARNING: could not find valid kd_threshold: resorting to 0.0')
	try: 
		fc_threshold = max(valid_thresholds_npv) # highest threshold below which NPV >= 0.95 (predict FC)
	except: 
		fc_threshold = 1.0
		print('WARNING: could not find valid fc_threshold: resorting to 1.0')
	return (fc_threshold, kd_threshold)

# Get TN, FP, FN, TP, fc_indeterminate, kd_indeterminate for given y_prob and y_test
def compute_indeterminate_confusion(y_prob, y_test, fc_kd_thresholds=None):
	# Threshold y_prob, get predictions
	if fc_kd_thresholds == None:
		fc_threshold, kd_threshold = get_fc_kd_thresholds(y_prob, y_test)
	else:
		fc_threshold, kd_threshold = fc_kd_thresholds
	fc_binary = np.array(y_prob <= fc_threshold).astype(np.int32) # where y_prob <= fc_threshold
	kd_binary = np.array(y_prob >= kd_threshold).astype(np.int32) # where y_prob >= kd_threshold
	indeterminate_binary = np.array(np.logical_and(y_prob > fc_threshold, y_prob < kd_threshold)).astype(np.int32)

	# Get TP, TN, FP, FN, Indeterminates
	true_negatives = np.sum(fc_binary * (1 - y_test)) # fc_binary = 1 and y_test = 0
	false_positives = np.sum(kd_binary * (1 - y_test)) # kd_binary = 1 and y_test = 0
	false_negatives = np.sum(fc_binary * y_test) # fc_binary = 1 and y_test = 1
	true_positives = np.sum(kd_binary * y_test) # kd_binary = 1 and y_test = 1
	fc_indeterminate = np.sum(indeterminate_binary * (1 - y_test)) # indeterminate_binary = 1 and y_test = 0
	kd_indeterminate = np.sum(indeterminate_binary * y_test) # indeterminate_binary = 1 and y_test = 1

	return (true_negatives, false_positives, false_negatives, true_positives, fc_indeterminate, kd_indeterminate)

# Train and evaluate model using K-Fold CV, print out results, return ROC curves from each split
	# return_val: 'roc_auc' (OOS ROCAUC), 'roc_curves' (sklearn-style ROC curve), or 'roc_confusion' (ROC, Confusion tuple)
def test_model(model, x, y, 
		threshold=0.5, allow_indeterminates=True, 
		calibration_set_size=0.5,
		return_val='roc_auc', random_state=90007):
	stats_arr = []
	best_scores = []
	oos_roc_curves = [] # out-of-sample ROC curves
	oos_roc_scores = [] # out-of-sample ROC scores
	kf = StratifiedKFold(n_splits=5, shuffle=True, random_state=random_state)
	for train_idx, test_idx in kf.split(x, y):
		# Unpack CV split
		x_train_all, x_test, y_train_all, y_test = x[train_idx], x[test_idx], y[train_idx], y[test_idx]
		# Separate risk-calibration set
		x_train, x_calibrate, y_train, y_calibrate = train_test_split(x_train_all, y_train_all, 
			test_size=calibration_set_size, random_state=random_state, stratify=y_train_all)

		### ROC EVALUATION ###
		# Train on non-calibration train set
		best_score = model.train(x_train, y_train)
		best_scores.append(best_score)
		y_prob = model.predict_proba(x_test)
		y_pred = model.predict(x_test, threshold=threshold)

		# Get ROC curve
		roc = roc_curve(y_test, y_prob) # tuple (fpr, tpr, thresholds)
		oos_roc_curves.append(roc)
		oos_roc_scores.append(auc(roc[0], roc[1]))

		### CONFUSION/THRESHOLDING EVALUATION ###
		# Confusion info
		if allow_indeterminates == False:
			stats_arr.append(compute_confusion(y_pred, y_test)) # confusion matrix with 1 set threshold
		else:
			y_calibrate_prob = model.predict_proba(x_calibrate)
			y_test_prob = model.predict_proba(x_test)
			fc_kd_thresholds = get_fc_kd_thresholds(y_calibrate_prob, y_calibrate) # risk calibration
			stats_arr.append(compute_indeterminate_confusion(y_test_prob, y_test, fc_kd_thresholds)) # confusion matrix with indeterminates

	print('CV Confusion: ', stats_arr)
	print('Best CV scores: ', np.around(best_scores, decimals=4))
	print('Avg best CV scores: ', np.mean(best_scores))
	print('Avg out-of-sample ROCAUC: ', np.mean(oos_roc_scores))

	total_confusion = np.sum(stats_arr, axis=0).tolist()
	explain_confusion(total_confusion, indeterminates=allow_indeterminates)

	if return_val == 'roc_auc': 
		return np.mean(oos_roc_scores) # mean ROCAUC
	elif return_val == 'roc_curves':
		return oos_roc_curves
	elif return_val == 'roc_confusion':
		return (np.mean(oos_roc_scores), total_confusion)


# Train and evaluate 2-stage model using K-Fold CV, print out results, return ROC curves from each split
	# return_val: 'roc_auc' (OOS ROCAUC), 'roc_curves' (sklearn-style ROC curve), or 'roc_confusion' (ROC, Confusion tuple)
def test_2stage_model(model, x, y, allow_indeterminates=True, final_threshold=0.5,
		calibration_set_size=0.5, return_val='roc_auc', random_state=90007):
	stats_arr = []
	# best_scores = [] (no best score because no GridSearchCV)
	oos_roc_curves = [] # out-of-sample ROC curves
	oos_roc_scores = [] # out-of-sample ROC scores

	num_stage1_kd = []
	num_stage1_fc = []
	num_stage1_indeterminate = []

	kf = StratifiedKFold(n_splits=5, shuffle=True, random_state=random_state)
	for train_idx, test_idx in kf.split(x, y):
		# Unpack CV split
		x_train_all, x_test, y_train_all, y_test = x[train_idx], x[test_idx], y[train_idx], y[test_idx]
		
		### --- ROC EVALUATION --- ###
		# Pestage2orm model-training and risk-calibration
		model.train_calibrate(x_train_all, y_train_all, calibration_set_size=calibration_set_size, random_state=random_state, refit=False) 
		y_prob = model.predict_proba(x_test)

		# Get ROC curve
		roc = roc_curve(y_test, y_prob) # tuple (fpr, tpr, thresholds)
		oos_roc_curves.append(roc)
		oos_roc_scores.append(auc(roc[0], roc[1]))

		### --- CONFUSION/THRESHOLDING EVALUATION --- ###
		stage1_y_prob = model.stage1.predict_proba(x_test)[:, 1]
		stage2_y_prob = model.stage2.predict_proba(x_test)[:, 1]
		y_prob = model.predict_proba(x_test)

		# Get thresholds from prior calibration
		stage1_fc_threshold, stage1_kd_threshold = model.stage1_fc_threshold, model.stage1_kd_threshold
		stage2_fc_threshold, stage2_kd_threshold = model.stage2_fc_threshold, model.stage2_kd_threshold

		# Stage 1 predictions
		stage1_fc_binary = np.array(stage1_y_prob <= stage1_fc_threshold).astype(np.int32) # where stage1_y_prob <= stage1_fc_threshold
		stage1_kd_binary = np.array(stage1_y_prob >= stage1_kd_threshold).astype(np.int32) # where stage1_y_prob >= stage1_kd_threshold
		stage1_indeterminate_binary = np.array(np.logical_and(stage1_y_prob > stage1_fc_threshold, stage1_y_prob < stage1_kd_threshold)).astype(np.int32)
		stage1_indeterminate_inds = np.argwhere(stage1_indeterminate_binary == 1)

		# Record how many patients are KD/FC/indeterminate after stage 1
		num_stage1_kd.append(np.sum(stage1_fc_binary))
		num_stage1_fc.append(np.sum(stage1_kd_binary))
		num_stage1_indeterminate.append(np.sum(stage1_indeterminate_binary))

		# Prep for Stage 2
		final_fc_binary = np.copy(stage1_fc_binary)
		final_kd_binary = np.copy(stage1_kd_binary)
		final_indeterminate_binary = np.copy(stage1_indeterminate_binary)

		# Allow indeterminates in final stage: perform PPV/NPV thresholding
		if allow_indeterminates == True:
			# Stage 2 predictions
			stage2_fc_binary = np.array(stage2_y_prob <= stage2_fc_threshold).astype(np.int32) # where stage2_y_prob <= stage2_fc_threshold
			stage2_kd_binary = np.array(stage2_y_prob >= stage2_kd_threshold).astype(np.int32) # where stage2_y_prob <= stage2_fc_threshold
			stage2_non_indeterminate = np.array(np.logical_or(stage2_fc_binary, stage2_kd_binary)) # where a prediction was made by stage2 (non-indeterminate)

			# Apply stage2 predictions
			final_fc_binary[stage1_indeterminate_inds] = stage2_fc_binary[stage1_indeterminate_inds] # apply stage2 FC predictions to indeterminates
			final_kd_binary[stage1_indeterminate_inds] = stage2_kd_binary[stage1_indeterminate_inds] # apply stage2 KD predictions to indeterminates
			final_indeterminate_binary[stage1_indeterminate_inds] = stage2_non_indeterminate[stage1_indeterminate_inds] # update indeterminate entries

			# Get TP, TN, FP, FN, Indeterminates
			true_negatives = np.sum(final_fc_binary * (1 - y_test)) # fc_binary = 1 and y_test = 0
			false_positives = np.sum(final_kd_binary * (1 - y_test)) # kd_binary = 1 and y_test = 0
			false_negatives = np.sum(final_fc_binary * y_test) # fc_binary = 1 and y_test = 1
			true_positives = np.sum(final_kd_binary * y_test) # kd_binary = 1 and y_test = 1
			fc_indeterminate = np.sum(final_indeterminate_binary * (1 - y_test)) # indeterminate_binary = 1 and y_test = 0
			kd_indeterminate = np.sum(final_indeterminate_binary * y_test) # indeterminate_binary = 1 and y_test = 1

			stats_arr.append((true_negatives, false_positives, false_negatives, true_positives, fc_indeterminate, kd_indeterminate))

		# No indeterminates in final stage: threshold at 0.5 (or manually pass in "final_threshold")
		else:
			# Stage 2 predictions
			stage2_fc_binary = np.array(stage2_y_prob <= final_threshold).astype(np.int32) # where stage2_y_prob <= final_threshold
			stage2_kd_binary = np.array(stage2_y_prob > final_threshold).astype(np.int32) # where stage2_y_prob < final_threshold

			# Apply stage2 predictions
			final_fc_binary[stage1_indeterminate_inds] = stage2_fc_binary[stage1_indeterminate_inds] # apply stage2 FC predictions to indeterminates
			final_kd_binary[stage1_indeterminate_inds] = stage2_kd_binary[stage1_indeterminate_inds] # apply stage2 KD predictions to indeterminates

			# Get TP, TN, FP, FN, Indeterminates
			true_negatives = np.sum(final_fc_binary * (1 - y_test)) # fc_binary = 1 and y_test = 0
			false_positives = np.sum(final_kd_binary * (1 - y_test)) # kd_binary = 1 and y_test = 0
			false_negatives = np.sum(final_fc_binary * y_test) # fc_binary = 1 and y_test = 1
			true_positives = np.sum(final_kd_binary * y_test) # kd_binary = 1 and y_test = 1

			stats_arr.append((true_negatives, false_positives, false_negatives, true_positives))
		
	print('Total Stage-1 KD/FC/Indeterminate: {}/{}/{}'.format(np.sum(num_stage1_kd), np.sum(num_stage1_fc), np.sum(num_stage1_indeterminate)))
	print('CV Confusion: ', stats_arr)
	print('Avg out-of-sample ROCAUC: ', np.mean(oos_roc_scores))

	total_confusion = np.sum(stats_arr, axis=0).tolist()
	explain_confusion(total_confusion, indeterminates=allow_indeterminates)

	if return_val == 'roc_auc': 
		return np.mean(oos_roc_scores) # mean ROCAUC
	elif return_val == 'roc_curves':
		return oos_roc_curves
	elif return_val == 'roc_confusion':
		return (np.mean(oos_roc_scores), total_confusion)

# Plot ROC Curves from K-Fold CV, show mean, variance across K-folds
	# Takes in a list of (fpr-array, tpr-array, threshold-array) tuples
def plot_cv_roc_curves(roc_curves):
	plt.figure(figsize=(10, 8))
	tprs = []
	aucs = []
	mean_fpr = np.linspace(0, 1, 100)

	i = 0
	for fpr, tpr, thresholds in roc_curves:
		tprs.append(interp(mean_fpr, fpr, tpr))
		tprs[-1][0] = 0.0
		roc_auc = auc(fpr, tpr)
		aucs.append(roc_auc)
		plt.plot(fpr, tpr, lw=1, alpha=0.3,
				 label='ROC fold %d (AUC = %0.3f)' % (i, roc_auc))

		i += 1
	plt.plot([0, 1], [0, 1], linestyle='--', lw=2, color='r',
			 label='Luck', alpha=.8)

	mean_tpr = np.mean(tprs, axis=0)
	mean_tpr[-1] = 1.0
	mean_auc = auc(mean_fpr, mean_tpr)
	std_auc = np.std(aucs)
	plt.plot(mean_fpr, mean_tpr, color='b',
			 label=r'Mean ROC (AUC = %0.3f $\pm$ %0.3f)' % (mean_auc, std_auc),
			 lw=2, alpha=.8)

	std_tpr = np.std(tprs, axis=0)
	tprs_upper = np.minimum(mean_tpr + std_tpr, 1)
	tprs_lower = np.maximum(mean_tpr - std_tpr, 0)
	plt.fill_between(mean_fpr, tprs_lower, tprs_upper, color='grey', alpha=.2,
					 label=r'$\pm$ 1 std. dev.')

	plt.xlim([-0.05, 1.05])
	plt.ylim([-0.05, 1.05])
	plt.xticks(np.arange(0, 1.05, step=0.05))
	plt.yticks(np.arange(0, 1.05, step=0.05))
	plt.xlabel('False Positive Rate (1 - Specificity)')
	plt.ylabel('True Positive Rate (Sensitivity)')
	plt.title('ROC Curves Across K-Folds (Interpolated)')
	plt.legend(loc="lower right")
	plt.grid(True)
	plt.show()
	
# ScikitModel wrapper class
class ScikitModel:
	def __init__(self, skmodel, params, random_search=False, n_iter=10, scoring='roc_auc', beta=1.0, n_jobs=1, verbose=False):
		self.skmodel = skmodel
		self.cv_scorer = 'roc_auc' if scoring=='roc_auc' else make_scorer(fbeta_score, beta=beta)
		self.verbose = verbose
		if random_search == True: # Randomized grid search
			self.paramsearch = RandomizedSearchCV(self.skmodel, params, cv=5, 
										n_iter=n_iter,
										scoring=self.cv_scorer, 
										verbose=verbose,
										n_jobs=n_jobs)
		else: # Regular grid search
			self.paramsearch = GridSearchCV(self.skmodel, params, cv=5,
										scoring=self.cv_scorer, 
										verbose=verbose,
										n_jobs=n_jobs)
		
	# Run CV fit on x_train, y_train
	def train(self, x_train, y_train):
		self.paramsearch.fit(x_train, y_train)
		if self.verbose >= 1:
			print('Best params: ', self.paramsearch.best_params_)
			print('Best score: ', self.paramsearch.best_score_)
		return self.paramsearch.best_score_ # return ROC-AUC or f-beta
	
	# Predict on x_test, return probability that each patient is KD
	def predict_proba(self, x_test):
		y_prob = self.paramsearch.predict_proba(x_test)[:, 1]
		return y_prob
	
	# Predict on x_test, return binary y_pred
	def predict(self, x_test, threshold=0.5):
		y_prob = self.predict_proba(x_test) # probability of KD
		y_pred = apply_threshold(y_prob, threshold)
		return y_pred

	# Train on x_train and y_train, and predict on x_test
	def train_test(self, x_train, x_test, y_train, y_test, threshold=0.5):
		self.train(x_train, y_train)
		return self.predict(x_test, threshold=threshold)



# 2-stage model wrapper class
class TwoStageModel:
	def __init__(self, stage1_model, stage2_model,
			stage2_fc_threshold=0.4, stage2_kd_threshold=0.6,
			verbose=True): # had to hardcode thresholds because they overlapped
		self.stage1 = stage1_model
		self.stage2 = stage2_model

		self.stage2_fc_threshold = stage2_fc_threshold
		self.stage2_kd_threshold = stage2_kd_threshold

		self.verbose = verbose
		self.calibrated = False

	# Train & Calibrate model (fit stage1 and stage2 on half of train-set, perform calibration on other set)
		# Store thresholds in self.{stage1/stage2}_{kd/fc}_threshold
		# If refit=True, refit stage1 and stage2 on entire train-set for inference
	def train_calibrate(self, x_train, y_train, calibration_set_size=0.5, random_state=90007, refit=False):
		# Split train and calibrate sets
		x_train_calibrate, x_calibrate, y_train_calibrate, y_calibrate = train_test_split(x_train, y_train, 
			test_size=calibration_set_size, random_state=random_state, stratify=y_train)

		# Calibrate stage1
		self.stage1.fit(x_train_calibrate, y_train_calibrate)
		stage1_calibrate_proba = self.stage1.predict_proba(x_calibrate)[:, 1]
		self.stage1_fc_threshold, self.stage1_kd_threshold = get_fc_kd_thresholds(stage1_calibrate_proba, y_calibrate)

		# Calibrate stage2
		self.stage2.fit(x_train_calibrate, y_train_calibrate)
		stage2_calibrate_proba = self.stage1.predict_proba(x_calibrate)[:, 1]
		self.stage2_fc_threshold, self.stage2_kd_threshold = get_fc_kd_thresholds(stage2_calibrate_proba, y_calibrate)

		# Refit on entire train-set after calibration
		if refit == True:
			self.stage1.fit(x_train, y_train)
			self.stage2.fit(x_train, y_train)

		self.calibrated = True

	# Train only (fit stage1 and stage2) -- don't calibrate
	def train(self, x_train, y_train):
		self.stage1.fit(x_train, y_train)
		self.stage2.fit(x_train, y_train)

	# Predict on x_test, return probability that each patient is KD
	def predict_proba(self, x_test):
		if self.calibrated == False:
			print('WARNING: called predict_proba on Stanford model without pre-calibrating!')

		### Test ###
		stage1_test_proba = self.stage1.predict_proba(x_test)[:, 1]
		indeterminate_test = np.array(np.logical_and(stage1_test_proba > self.stage1_fc_threshold, stage1_test_proba < self.stage1_kd_threshold))

		x_indeterminate_test = x_test[indeterminate_test]

		final_proba = np.copy(stage1_test_proba)
		
		# If there are indeterminates, use stage2 to generate stage-2 predictions
		if x_indeterminate_test.shape[0] > 0:
			stage2_test_proba = self.stage2.predict_proba(x_indeterminate_test)[:, 1]
			final_indeterminate_test = np.zeros(indeterminate_test.shape, dtype=bool)
			final_indeterminate_test[indeterminate_test] = np.array(np.logical_and(stage2_test_proba > self.stage2_fc_threshold, stage2_test_proba < self.stage2_kd_threshold))
			final_proba[indeterminate_test] = stage2_test_proba

		return final_proba

	# Predict on x_test, return binary y_pred
	def predict(self, x_test, threshold=0.5):
		y_prob = self.predict_proba(x_test) # probability of KD
		y_pred = apply_threshold(y_prob, threshold)
		return y_pred

	# Train on x_train and y_train, and predict on x_test
	def train_test(self, x_train, x_test, y_train, y_test, threshold=0.5):
		self.train_calibrate(x_train, y_train)
		return self.predict(x_test, threshold=threshold)