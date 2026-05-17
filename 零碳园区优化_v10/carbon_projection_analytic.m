function zC = carbon_projection_analytic(targetC, data, rhoC)
%CARBON_PROJECTION_ANALYTIC Analytical projection for community carbon sharing.
%
% This version supports a separate ADMM penalty rhoC for carbon consensus.
%
% Default behavior follows the original code: only the first period carries
% inter-community carbon quota trading and sum_i zC(i,1)=0.
%
% Optional switch:
%   data.carbonTradeAllPeriods = true
% projects each period independently onto sum_i zC(i,t)=0.
%
% rhoC can be scalar or N-by-1. If rhoC is a vector, a weighted Euclidean
% projection is used:
%   min_z 0.5*sum_i rhoC_i*(z_i-target_i)^2, s.t. sum_i z_i = 0.

[N,T] = size(targetC);
zC = zeros(N,T);

if nargin < 3 || isempty(rhoC)
    rhoVec = ones(N,1);
elseif isscalar(rhoC)
    rhoVec = rhoC*ones(N,1);
else
    rhoVec = rhoC(:);
end
if numel(rhoVec) ~= N
    error('rhoC must be scalar or %d-element vector.', N);
end
if any(~isfinite(rhoVec)) || any(rhoVec <= 0)
    error('rhoC must contain positive finite values.');
end

tradeAllPeriods = true;
if nargin >= 2 && isstruct(data) && isfield(data, 'carbonTradeAllPeriods')
    tradeAllPeriods = logical(data.carbonTradeAllPeriods);
end

if tradeAllPeriods
    periods = 1:T;
else
    periods = 1;
end

invRho = 1 ./ rhoVec;
denom = sum(invRho);
for tt = periods
    nu = sum(targetC(:,tt)) / denom;
    zC(:,tt) = targetC(:,tt) - nu * invRho;
end
end
