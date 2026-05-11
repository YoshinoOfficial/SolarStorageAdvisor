function res = solve_admm_fixed(data)
% Fixed-rho ADMM for zero-carbon campus multi-energy model

optimizersPreprocessed = isfield(data, 'optimizersPreprocessed') && data.optimizersPreprocessed;
if ~optimizersPreprocessed
    yalmip('clear');
end
N = data.N; T = data.T;
rho = get_data_field(data, 'admmRho', 5);
rhoPQ = rho*ones(N,1);
maxIter = get_data_field(data, 'admmMaxIter', 1000);
tol_pri = get_data_field(data, 'admmTolPri', 5e-4);
tol_dual = get_data_field(data, 'admmTolDual', 5e-2);
beta_z = 1;
data.relaxBinary = false;
converged = false;

if optimizersPreprocessed
    fprintf('Using prebuilt optimizer cache for ADMM.\n');
else
    preprocess_optimizers(data, rhoPQ);
end

zP = zeros(N,T); zQ = zeros(N,T); zC = zeros(N,T);
lambdaP = zeros(N,T); lambdaQ = zeros(N,T); lambdaC = zeros(N,T);
sol = cell(N,1);
hist_pri = zeros(maxIter,1);
hist_dual = zeros(maxIter,1);
hist_cost = zeros(maxIter,1);

for it = 1:maxIter
    fprintf('Multi-energy fixed-ADMM iteration %d\n', it);
    zP_old = zP; zQ_old = zQ; zC_old = zC;
    totalLocalCost = 0;

    for i = 1:N
        p = build_local_params(data, i, zP, zQ, lambdaP(i,:), lambdaQ(i,:), rho, zC, lambdaC(i,:), rho);
        sol{i} = solve_local_subproblem(p);
        totalLocalCost = totalLocalCost + sol{i}.baseObj;
    end

    targetP = zeros(N,T); targetQ = zeros(N,T); targetC = zeros(N,T);
    for i = 1:N
        targetP(i,:) = sol{i}.PinjLocal + lambdaP(i,:)/rho;
        targetQ(i,:) = sol{i}.QinjLocal + lambdaQ(i,:)/rho;
        targetC(i,:) = sol{i}.QtradeLocal + lambdaC(i,:)/rho;
    end

    [zP_proj, zQ_proj, feeder] = feeder_projection(targetP, targetQ, data, rhoPQ);
    zP = beta_z*zP_proj + (1-beta_z)*zP_old;
    zQ = beta_z*zQ_proj + (1-beta_z)*zQ_old;
    zC_proj = zeros(N,T);
    zC_proj(:,1) = targetC(:,1) - mean(targetC(:,1));
    zC = beta_z*zC_proj + (1-beta_z)*zC_old;

    priPQ_sq = 0; dualPQ_sq = 0;
    for i = 1:N
        rP = sol{i}.PinjLocal - zP(i,:);
        rQ = sol{i}.QinjLocal - zQ(i,:);
        rC = sol{i}.QtradeLocal - zC(i,:);
        lambdaP(i,:) = lambdaP(i,:) + rho*rP;
        lambdaQ(i,:) = lambdaQ(i,:) + rho*rQ;
        lambdaC(i,:) = lambdaC(i,:) + rho*rC;
        priPQ_sq = priPQ_sq + sum(rP.^2) + sum(rQ.^2) + sum(rC.^2);
        dualPQ_sq = dualPQ_sq + (rho^2)*(sum((zP(i,:)-zP_old(i,:)).^2) + ...
            sum((zQ(i,:)-zQ_old(i,:)).^2) + sum((zC(i,:)-zC_old(i,:)).^2));
    end

    hist_pri(it) = sqrt(priPQ_sq);
    hist_dual(it) = sqrt(dualPQ_sq);
    hist_cost(it) = totalLocalCost;
    fprintf('  pri=%.6e  dual=%.6e  cost=%.6f\n', hist_pri(it), hist_dual(it), hist_cost(it));

    if hist_pri(it) < tol_pri && hist_dual(it) < tol_dual
        fprintf('Converged at iteration %d\n', it);
        hist_pri = hist_pri(1:it);
        hist_dual = hist_dual(1:it);
        hist_cost = hist_cost(1:it);
        converged = true;
        break;
    end
    if it == maxIter
        fprintf('Reached maxIter without strict convergence.\n');
        hist_pri = hist_pri(1:it);
        hist_dual = hist_dual(1:it);
        hist_cost = hist_cost(1:it);
    end
end

res = pack_res(data, sol, zP, zQ, zC, feeder, hist_pri, hist_dual, hist_cost, rho, ...
    'admm-fixed-multi-energy-pq-carbon', converged, tol_pri, tol_dual, maxIter);
end

function res = pack_res(data, sol, zP, zQ, zC, feeder, hist_pri, hist_dual, hist_cost, rho, methodName, converged, tol_pri, tol_dual, maxIter)
N = data.N; T = data.T;
fields = {'Pgrid','Pch','Pdis','SOC_e','PpvUse','PpvCurt','PwindUse','PwindCurt',...
          'uCh','Fgas','Pchp','Hchp','uChp','vStart','vStop','RupChp','RdnChp','Hdump', ...
          'Peb','Heb','RupEb','RdnEb','Pelec','H2prod','RupElec','RdnElec',...
          'H2cons_fc','Pfc','RupFc','RdnFc','Pcomp','RupComp','RdnComp','Hch','Hdis','SOC_th',...
          'H2ch','H2dis','SOC_h2','H2short','PinjLocal','QinjLocal','Qpv','Qes', ...
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
res.recoveredGlobalObjective = obj; res.parts = parts; res.rho = rho; res.rhoPQ = rho*ones(N,1); res.feeder = feeder;
res.finalPrimalResidual = hist_pri(end);
res.finalDualResidual = hist_dual(end);
res.maxConsensusP = max(abs(res.PinjLocal(:) - res.Pinj(:)));
res.maxConsensusQ = max(abs(res.QinjLocal(:) - res.Qinj(:)));
res.maxConsensusCarbon = max(abs(res.QtradeLocal(:) - res.Qtrade(:)));
res.admmTolPri = tol_pri;
res.admmTolDual = tol_dual;
res.admmMaxIter = maxIter;
carbon = carbon_accounting(data, res.Pgrid, res.Pchp, res.Hchp, res.Fgas);
res.CarbonEmission_kg = carbon.emission;
res.CarbonQuota_kg = carbon.quota;
res.CarbonAllowanceSurplus_kg = carbon.netAllowanceSurplus;
res.CarbonBuyMarket_kg = res.QaBuy;
res.CarbonSellMarket_kg = res.QaSell;
res.CarbonTradeWithCommunities_kg = res.Qtrade;
res.CarbonUnusedAllowance_kg = res.QaUnused;
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
