function res = solve_admm_fixed(data)
%SOLVE_ADMM_FIXED Fixed-rho ADMM for zero-carbon campus multi-energy model.
%
% Matrixized coordinator version with separated ADMM penalties:
%   1) Local community subproblems are kept as YALMIP optimizer models.
%   2) The feeder P/Q projection is solved as a sparse Gurobi QP with rhoPQ.
%   3) The community carbon-trading consensus projection is analytical with rhoC.
%
% ADMM penalty settings:
%   data.admmRhoPQ : P/Q feeder-consensus penalty (required, set by main function).
%   data.admmRhoC  : carbon-consensus penalty (required, set by main function).
%
% Stopping criterion:
%   hist_pri / hist_dual and hist_priP/Q/C / hist_dualP/Q/C are relative residuals.
%   Absolute residuals are kept in hist_pri_abs / hist_dual_abs and component *_abs fields.
%
% Switches:
%   data.useGurobiFeederProjection = true  (default)  use feeder_projection_gurobi
%   data.useGurobiFeederProjection = false            use original feeder_projection
%   data.allowFeederProjectionFallback = true(default) fallback to original feeder_projection

optimizersPreprocessed = isfield(data, 'optimizersPreprocessed') && data.optimizersPreprocessed;
if ~optimizersPreprocessed
    yalmip('clear');
end

N = data.N;
T = data.T;
rhoPQ = normalize_rho_vector(data.admmRhoPQ, N, 'admmRhoPQ');
rhoC  = normalize_rho_vector(data.admmRhoC,  N, 'admmRhoC');
rhoPQMat = repmat(rhoPQ(:), 1, T);
rhoCMat  = repmat(rhoC(:),  1, T);
maxIter = get_data_field(data, 'admmMaxIter', 1000);
tol_pri = get_data_field(data, 'admmTolPri', 5e-4);
tol_dual = get_data_field(data, 'admmTolDual', 5e-2);
beta_z = get_data_field(data, 'admmRelaxZ', 1);
useGurobiFeeder = logical(get_data_field(data, 'useGurobiFeederProjection', true));
allowFallback = logical(get_data_field(data, 'allowFeederProjectionFallback', true));
data.relaxBinary = false;
converged = false;

if optimizersPreprocessed
    fprintf('Using prebuilt local optimizer cache for ADMM.\n');
else
    preprocess_optimizers(data, rhoPQ, rhoC);
end

feederBase = [];
if useGurobiFeeder
    try
        feederBase = build_feeder_qp_base(data);
        fprintf('Using matrixized Gurobi feeder projection.\n');
    catch ME
        if allowFallback
            warning('Building Gurobi feeder QP base failed: %s. Falling back to YALMIP feeder_projection.', ME.message);
            useGurobiFeeder = false;
        else
            rethrow(ME);
        end
    end
end

zP = zeros(N,T);
zQ = zeros(N,T);
zC = zeros(N,T);
lambdaP = zeros(N,T);
lambdaQ = zeros(N,T);
lambdaC = zeros(N,T);
sol = cell(N,1);

hist_pri = zeros(maxIter,1);
hist_dual = zeros(maxIter,1);
hist_cost = zeros(maxIter,1);
hist_priP = zeros(maxIter,1);
hist_priQ = zeros(maxIter,1);
hist_priC = zeros(maxIter,1);
hist_dualP = zeros(maxIter,1);
hist_dualQ = zeros(maxIter,1);
hist_dualC = zeros(maxIter,1);

% Absolute residual histories are retained for diagnostics; the primary
% convergence histories above are relative residuals.
hist_pri_abs = zeros(maxIter,1);
hist_dual_abs = zeros(maxIter,1);
hist_priP_abs = zeros(maxIter,1);
hist_priQ_abs = zeros(maxIter,1);
hist_priC_abs = zeros(maxIter,1);
hist_dualP_abs = zeros(maxIter,1);
hist_dualQ_abs = zeros(maxIter,1);
hist_dualC_abs = zeros(maxIter,1);

hist_timeLocal = zeros(maxIter,1);
hist_timeFeeder = zeros(maxIter,1);

for it = 1:maxIter
    fprintf('Multi-energy fixed-ADMM iteration %d\n', it);
    zP_old = zP;
    zQ_old = zQ;
    zC_old = zC;
    totalLocalCost = 0;

    U_P = zeros(N,T);
    U_Q = zeros(N,T);
    U_C = zeros(N,T);

    tAllLocal = tic;
    for i = 1:N
        fprintf('  local community %d/%d ... ', i, N);
        drawnow;
        tLocal = tic;
        p = build_local_params(data, i, zP, zQ, lambdaP(i,:), lambdaQ(i,:), rhoPQ(i), zC, lambdaC(i,:), rhoC(i));
        candidate = solve_local_subproblem(p);
        localTime = toc(tLocal);
        if is_bad_local_solution(candidate, p)
            if it > 1 && ~isempty(sol{i}) && isfield(sol{i}, 'baseObj') && isfinite(sol{i}.baseObj)
                warning(['ADMM iteration %d community %d returned a suspicious local solution ', ...
                    '(baseObj=%.6g, elapsed=%.2f s). Reusing the previous valid local solution.'], ...
                    it, i, get_bad_baseobj(candidate), localTime);
            else
                error(['ADMM iteration %d community %d returned an invalid local solution ', ...
                    '(baseObj=%.6g, elapsed=%.2f s) and no previous valid solution exists. ', ...
                    'Inspect this community problem and the finite-field checks in is_bad_local_solution.'], ...
                    it, i, get_bad_baseobj(candidate), localTime);
            end
        else
            sol{i} = candidate;
        end
        fprintf('done in %.2f s, baseObj=%.6f\n', localTime, sol{i}.baseObj);
        drawnow;

        U_P(i,:) = sol{i}.PinjLocal;
        U_Q(i,:) = sol{i}.QinjLocal;
        U_C(i,:) = sol{i}.QtradeLocal;
        totalLocalCost = totalLocalCost + sol{i}.baseObj;
    end
    hist_timeLocal(it) = toc(tAllLocal);

    targetP = U_P + lambdaP ./ rhoPQMat;
    targetQ = U_Q + lambdaQ ./ rhoPQMat;
    targetC = U_C + lambdaC ./ rhoCMat;

    fprintf('  feeder projection ... ');
    drawnow;
    tFeeder = tic;
    if useGurobiFeeder
        try
            [zP_proj, zQ_proj, feeder] = feeder_projection_gurobi(targetP, targetQ, data, rhoPQ, feederBase);
        catch ME
            if allowFallback
                warning('Gurobi feeder projection failed at iteration %d: %s. Falling back to YALMIP feeder_projection.', it, ME.message);
                useGurobiFeeder = false;
                [zP_proj, zQ_proj, feeder] = feeder_projection(targetP, targetQ, data, rhoPQ);
            else
                rethrow(ME);
            end
        end
    else
        [zP_proj, zQ_proj, feeder] = feeder_projection(targetP, targetQ, data, rhoPQ);
    end
    hist_timeFeeder(it) = toc(tFeeder);
    fprintf('done in %.2f s\n', hist_timeFeeder(it));
    drawnow;

    zP = beta_z*zP_proj + (1-beta_z)*zP_old;
    zQ = beta_z*zQ_proj + (1-beta_z)*zQ_old;
    zC_proj = carbon_projection_analytic(targetC, data, rhoC);
    zC = beta_z*zC_proj + (1-beta_z)*zC_old;

    rP = U_P - zP;
    rQ = U_Q - zQ;
    rC = U_C - zC;

    lambdaP = lambdaP + rhoPQMat .* rP;
    lambdaQ = lambdaQ + rhoPQMat .* rQ;
    lambdaC = lambdaC + rhoCMat  .* rC;

    sP = rhoPQMat .* (zP - zP_old);
    sQ = rhoPQMat .* (zQ - zQ_old);
    sC = rhoCMat  .* (zC - zC_old);

    % Absolute residuals.
    hist_priP_abs(it) = norm(rP(:),2);
    hist_priQ_abs(it) = norm(rQ(:),2);
    hist_priC_abs(it) = norm(rC(:),2);
    hist_dualP_abs(it) = norm(sP(:),2);
    hist_dualQ_abs(it) = norm(sQ(:),2);
    hist_dualC_abs(it) = norm(sC(:),2);
    hist_pri_abs(it) = norm([rP(:); rQ(:); rC(:)], 2);
    hist_dual_abs(it) = norm([sP(:); sQ(:); sC(:)], 2);

    % Relative residuals used for ADMM stopping.  The denominator is at least
    % one to avoid division by zero when a block is inactive, e.g. carbon trade.
    hist_priP(it) = relative_residual(rP, U_P, zP);
    hist_priQ(it) = relative_residual(rQ, U_Q, zQ);
    hist_priC(it) = relative_residual(rC, U_C, zC);
    hist_dualP(it) = relative_residual(sP, rhoPQMat .* zP, rhoPQMat .* zP_old);
    hist_dualQ(it) = relative_residual(sQ, rhoPQMat .* zQ, rhoPQMat .* zQ_old);
    hist_dualC(it) = relative_residual(sC, rhoCMat  .* zC, rhoCMat  .* zC_old);
    hist_pri(it) = relative_residual([rP(:); rQ(:); rC(:)], ...
        [U_P(:); U_Q(:); U_C(:)], [zP(:); zQ(:); zC(:)]);
    hist_dual(it) = relative_residual([sP(:); sQ(:); sC(:)], ...
        [rhoPQMat(:).*zP(:); rhoPQMat(:).*zQ(:); rhoCMat(:).*zC(:)], ...
        [rhoPQMat(:).*zP_old(:); rhoPQMat(:).*zQ_old(:); rhoCMat(:).*zC_old(:)]);
    hist_cost(it) = totalLocalCost;

    fprintf(['  rel_pri=%.6e  rel_dual=%.6e  cost=%.6f  ', ...
             '[rP=%.3e rQ=%.3e rC=%.3e | sP=%.3e sQ=%.3e sC=%.3e]\n'], ...
        hist_pri(it), hist_dual(it), hist_cost(it), ...
        hist_priP(it), hist_priQ(it), hist_priC(it), ...
        hist_dualP(it), hist_dualQ(it), hist_dualC(it));
    fprintf(['  abs_pri=%.6e  abs_dual=%.6e  ', ...
             '[rP=%.3e rQ=%.3e rC=%.3e | sP=%.3e sQ=%.3e sC=%.3e]\n'], ...
        hist_pri_abs(it), hist_dual_abs(it), ...
        hist_priP_abs(it), hist_priQ_abs(it), hist_priC_abs(it), ...
        hist_dualP_abs(it), hist_dualQ_abs(it), hist_dualC_abs(it));

    if hist_pri(it) < tol_pri && hist_dual(it) < tol_dual
        fprintf('Converged by relative residuals at iteration %d\n', it);
        converged = true;
        break;
    end
    if it == maxIter
        fprintf('Reached maxIter without strict convergence.\n');
    end
end

lastIter = it;
hist_pri = hist_pri(1:lastIter);
hist_dual = hist_dual(1:lastIter);
hist_cost = hist_cost(1:lastIter);
hist_pri_abs = hist_pri_abs(1:lastIter);
hist_dual_abs = hist_dual_abs(1:lastIter);

res = pack_res(data, sol, zP, zQ, zC, feeder, hist_pri, hist_dual, hist_cost, rhoPQ, rhoC, ...
    'admm-fixed-multi-energy-rhoPQ-rhoC-relative-residual-gurobi-feeder', converged, tol_pri, tol_dual, maxIter);
res.useGurobiFeederProjection = useGurobiFeeder;
res.hist_priP = hist_priP(1:lastIter);
res.hist_priQ = hist_priQ(1:lastIter);
res.hist_priC = hist_priC(1:lastIter);
res.hist_dualP = hist_dualP(1:lastIter);
res.hist_dualQ = hist_dualQ(1:lastIter);
res.hist_dualC = hist_dualC(1:lastIter);

% Relative residuals are stored in the legacy hist_* fields for plotting and
% summary compatibility.  Absolute residuals are stored separately.
res.hist_pri_abs = hist_pri_abs;
res.hist_dual_abs = hist_dual_abs;
res.hist_priP_abs = hist_priP_abs(1:lastIter);
res.hist_priQ_abs = hist_priQ_abs(1:lastIter);
res.hist_priC_abs = hist_priC_abs(1:lastIter);
res.hist_dualP_abs = hist_dualP_abs(1:lastIter);
res.hist_dualQ_abs = hist_dualQ_abs(1:lastIter);
res.hist_dualC_abs = hist_dualC_abs(1:lastIter);
res.finalPrimalResidualAbs = hist_pri_abs(end);
res.finalDualResidualAbs = hist_dual_abs(end);
res.residualCriterion = 'relative';
res.hist_timeLocal = hist_timeLocal(1:lastIter);
res.hist_timeFeeder = hist_timeFeeder(1:lastIter);
end

function tf = is_bad_local_solution(candidate, p) %#ok<INUSD>
%IS_BAD_LOCAL_SOLUTION Validate numerical integrity of a local optimizer output.
%
% Do NOT reject a solution only because baseObj <= 0. Under a fixed carbon
% allowance baseline and allowed carbon-market selling, a community can obtain
% carbon allowance revenue, so the local economic cost may legitimately be
% negative. The previous baseObj<=0 test caused false ADMM failures in high
% renewable scenarios.
tf = true;

if ~isstruct(candidate) || ~isfield(candidate, 'baseObj') || ...
        ~isnumeric(candidate.baseObj) || ~isscalar(candidate.baseObj) || ...
        ~isfinite(candidate.baseObj)
    return;
end

requiredFields = {'Pgrid','PinjLocal','QinjLocal','QtradeLocal', ...
    'PpvUse','PwindUse','Pchp','Hchp','Fgas','Qwind','QaBuy','QaSell','QaUnused'};
for kk = 1:numel(requiredFields)
    f = requiredFields{kk};
    if ~isfield(candidate, f)
        return;
    end
    x = candidate.(f);
    if ~isnumeric(x) || any(~isfinite(x(:)))
        return;
    end
    if any(abs(x(:)) > 1e8)
        return;
    end
end

tf = false;
end

function x = get_bad_baseobj(candidate)
if isstruct(candidate) && isfield(candidate, 'baseObj') && isnumeric(candidate.baseObj) && isscalar(candidate.baseObj)
    x = candidate.baseObj;
else
    x = NaN;
end
end
function res = pack_res(data, sol, zP, zQ, zC, feeder, hist_pri, hist_dual, hist_cost, rhoPQ, rhoC, methodName, converged, tol_pri, tol_dual, maxIter)
N = data.N; T = data.T;
fields = {'Pgrid','Pch','Pdis','SOC_e','PpvUse','PpvCurt','PwindUse','PwindCurt',...
          'uCh','Fgas','Pchp','Hchp','uChp','vStart','vStop','RupChp','RdnChp','Hdump', ...
          'Peb','Heb','RupEb','RdnEb','Pelec','H2prod','RupElec','RdnElec',...
          'H2cons_fc','Pfc','RupFc','RdnFc','Pcomp','RupComp','RdnComp','Hch','Hdis','SOC_th',...
          'H2ch','H2dis','SOC_h2','H2short','PdrShift','PdrShiftDev','PdrCutE','HdrCut','H2drCut', ...
          'PloadDR','HloadDR','H2loadDR','PinjLocal','QinjLocal','Qpv','Qwind','Qes', ...
          'QaBuy','QaSell','QtradeLocal','QaUnused'};
for f = 1:numel(fields), res.(fields{f}) = zeros(N,T); end
for i = 1:N
    for f = 1:numel(fields)
        if isfield(sol{i}, fields{f}), res.(fields{f})(i,:) = sol{i}.(fields{f}); end
    end
end
[obj, parts] = recover_global_objective(data, sol);
res.method = methodName;
res.Pinj = zP; res.Qinj = zQ;
res.Qtrade = zC;
res.Pij = feeder.Pij; res.Qij = feeder.Qij;
res.V = feeder.V;
res.hist_pri = hist_pri; res.hist_dual = hist_dual; res.hist_cost = hist_cost;
res.finalLocalCost = hist_cost(end);
res.recoveredGlobalObjective = obj; res.parts = parts; res.rhoPQ = rhoPQ(:); res.rhoC = rhoC(:); res.rho = mean(rhoPQ(:)); res.feeder = feeder;
res.finalPrimalResidual = hist_pri(end);
res.finalDualResidual = hist_dual(end);
res.maxConsensusP = max(abs(res.PinjLocal(:) - res.Pinj(:)));
res.maxConsensusQ = max(abs(res.QinjLocal(:) - res.Qinj(:)));
res.maxConsensusCarbon_tCO2 = max(abs(res.QtradeLocal(:) - res.Qtrade(:)));
res.maxConsensusCarbon_kg = 1000*res.maxConsensusCarbon_tCO2;
% Keep the legacy field in kgCO2 because existing summary scripts write MaxConsensusCarbon_kg from this field.
res.maxConsensusCarbon = res.maxConsensusCarbon_kg;
res.admmTolPri = tol_pri;
res.admmTolDual = tol_dual;
res.admmMaxIter = maxIter;
carbon = carbon_accounting(data, res.Pgrid, res.Pchp, res.Hchp, res.Fgas);
res.CarbonEmission_kg = carbon.emission;
res.CarbonQuota_kg = carbon.quota;
res.CarbonAllowanceSurplus_kg = carbon.netAllowanceSurplus;
res.CarbonBuyMarket_tCO2 = res.QaBuy;
res.CarbonSellMarket_tCO2 = res.QaSell;
res.CarbonTradeWithCommunities_tCO2 = res.Qtrade;
res.CarbonUnusedAllowance_tCO2 = res.QaUnused;
% Backward-compatible kgCO2 fields for existing summary/export scripts.
res.CarbonBuyMarket_kg = 1000*res.QaBuy;
res.CarbonSellMarket_kg = 1000*res.QaSell;
res.CarbonTradeWithCommunities_kg = 1000*res.Qtrade;
res.CarbonUnusedAllowance_kg = 1000*res.QaUnused;
res.CarbonTradingCost_Yuan = get_part(parts, 'carbonTradingCost');
res.TotalObjective_Yuan = obj;
res.Iterations = numel(hist_pri);
if converged
    res.Status = 'Solved';
else
    res.Status = 'MaxIterNotConverged';
end
res.totalPVCurt = sum(res.PpvCurt(:)); res.totalWindCurt = sum(res.PwindCurt(:));
res.totalPVUse = sum(res.PpvUse(:)); res.totalWindUse = sum(res.PwindUse(:));
res.totalGas = sum(res.Fgas(:)); res.totalH2short = sum(res.H2short(:));
res.totalHdump = sum(res.Hdump(:));
res.totalPdrShiftDev = sum(res.PdrShiftDev(:))*data.dt;
res.totalPdrCutE = sum(res.PdrCutE(:))*data.dt;
res.totalHdrCut = sum(res.HdrCut(:))*data.dt;
res.totalH2drCut = sum(res.H2drCut(:))*data.dt;
end



function val = relative_residual(err, varargin)
%RELATIVE_RESIDUAL Scale a residual by the largest relevant reference norm.
% The lower bound 1 keeps inactive or zero-valued consensus blocks from
% generating NaN/Inf values and makes the criterion dimensionless.
denom = 1;
for kk = 1:numel(varargin)
    x = varargin{kk};
    if ~isempty(x)
        denom = max(denom, norm(x(:), 2));
    end
end
val = norm(err(:), 2) / denom;
end

function rhoVec = normalize_rho_vector(raw, N, name)
if isempty(raw)
    error('%s cannot be empty.', name);
end
if isscalar(raw)
    rhoVec = raw*ones(N,1);
else
    rhoVec = raw(:);
end
if numel(rhoVec) ~= N
    error('%s must be scalar or %d-element vector.', name, N);
end
if any(~isfinite(rhoVec)) || any(rhoVec <= 0)
    error('%s must contain positive finite values.', name);
end
end

function val = get_data_field(s, name, defaultVal)
if isfield(s, name) && ~isempty(s.(name))
    val = s.(name);
else
    val = defaultVal;
end
end

function val = get_part(parts, name)
if isfield(parts, name)
    val = parts.(name);
else
    val = 0;
end
end


