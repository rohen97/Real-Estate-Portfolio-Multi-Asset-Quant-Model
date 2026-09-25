const probability = (value: unknown) => typeof value === 'number' && Number.isFinite(value) && value >= 0 && value <= 1;

function unavailable(record: any) {
  return [record?.status, record?.confidence_status, record?.legal_status].some(value =>
    /fixture|fictional|not_trained|untrained|not_estimated|uncalibrated/i.test(value || ''));
}

/** Numeric display fixtures are not evidence of a fitted, calibrated model. */
export function canShowZoningConfidence(record: any, collection?: any): boolean {
  const model = record?.prediction || record, core = model?.core || record;
  const trained = model?.trained === true || model?.model_validation?.status === 'validated';
  const calibrated = model?.calibrated === true || !!model?.probability_calibration?.core || record?.confidence_status === 'calibrated';
  return !unavailable(collection) && !unavailable(record) && !unavailable(model)
    && model?.trained !== false && model?.synthetic_training !== true && model?.calibrated !== false
    && trained && calibrated && core?.abstain === false
    && probability(core?.confidence) && probability(core?.entropy);
}

export function canShowZoningChange(record: any, collection?: any): boolean {
  const change = record?.future_change || record;
  return !unavailable(collection) && !unavailable(record) && !unavailable(change)
    && change?.trained === true && change?.synthetic_training !== true && change?.calibrated === true
    && change?.abstain !== true && probability(change?.change_probability);
}
