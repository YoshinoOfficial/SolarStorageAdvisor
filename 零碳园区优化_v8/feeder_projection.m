function [zP, zQ, feeder] = feeder_projection(varargin)
%FEEDER_PROJECTION
% Parameterized feeder P/Q projection with persistent optimizer cache.
%
% Usage:
%   [zP, zQ, feeder] = feeder_projection(targetP, targetQ, data, rhoPQ)
%   feeder_projection('clear_cache')
%   feeder_projection('prebuild', data, rhoPQ)

persistent CACHE
CACHE = feeder_init_cache(CACHE);

if nargin >= 1 && (ischar(varargin{1}) || isstring(varargin{1}))
    cmd = lower(char(varargin{1}));
    switch cmd
        case 'clear_cache'
            CACHE = feeder_init_cache([]);
            zP = []; zQ = []; feeder = struct();
            return;
        case 'prebuild'
            if nargin < 3
                error('feeder_projection(''prebuild'', data, rhoPQ) requires both data and rhoPQ.');
            end
            data = varargin{2}; rhoPQ = varargin{3};
            [~, CACHE] = feeder_get_or_build_cache(data, rhoPQ, CACHE);
            zP = []; zQ = []; feeder = struct();
            return;
        otherwise
            error('Unknown command: %s', cmd);
    end
end

if nargin ~= 4
    error('feeder_projection expects targetP, targetQ, data, rhoPQ.');
end

targetP = varargin{1};
targetQ = varargin{2};
data    = varargin{3};
rhoPQ   = varargin{4};

[cache, CACHE] = feeder_get_or_build_cache(data, rhoPQ, CACHE);
paramVec = feeder_pack_parameters(targetP, targetQ, rhoPQ);

try
    solVec = cache.opt(paramVec);
catch ME
    warning('Feeder optimizer cache retry: %s', ME.message);
    try, yalmip('clear'); catch, end
    CACHE = feeder_init_cache([]);
    [cache, CACHE] = feeder_get_or_build_cache(data, rhoPQ, CACHE);
    paramVec = feeder_pack_parameters(targetP, targetQ, rhoPQ);
    try
        solVec = cache.opt(paramVec);
    catch ME2
        error('Feeder optimizer failed: %s', ME2.message);
    end
end

[zP, zQ, feeder] = feeder_unpack_solution(solVec, cache);
end

function CACHE = feeder_init_cache(CACHE)
if isempty(CACHE)
    CACHE = containers.Map('KeyType','char','ValueType','any');
end
end

function [cache, CACHE] = feeder_get_or_build_cache(data, rhoPQ, CACHE)
CACHE = feeder_init_cache(CACHE);
key = feeder_cache_key(data, rhoPQ);
if isKey(CACHE, key)
    cache = CACHE(key);
    return;
end
cache = feeder_compile_optimizer(data, rhoPQ);
CACHE(key) = cache;
end

function key = feeder_cache_key(data, rhoPQ)
key = sprintf(['N=%d|T=%d|B=%d|L=%d|root=%d|rho=%s|branch=%s|r=%s|x=%s|Vsl=%.12g|' ...
               'Vmin=%s|Vmax=%s|Pgrid=%s|Qmin=%s|Qmax=%s|Pbus=%s|Qbus=%s|Pij=%s|Qij=%s|' ...
               'Psub=%s|hascomm=%s|map=%s|baseMVA=%.12g'], ...
    data.N, data.T, data.B, data.L, data.rootBus, feeder_sig(rhoPQ), ...
    feeder_sig(data.branch), feeder_sig(data.rline), feeder_sig(data.xline), data.Vslack, ...
    feeder_sig(data.Vmin), feeder_sig(data.Vmax), feeder_sig(data.PgridMax), ...
    feeder_sig(data.QinjMin), feeder_sig(data.QinjMax), feeder_sig(data.PbusBase), ...
    feeder_sig(data.QbusBase), feeder_sig(data.PijMax), feeder_sig(data.QijMax), ...
    feeder_sig(data.PsubMax), feeder_sig(double(data.bus_has_comm)), feeder_sig(data.bus_to_comm), data.baseMVA);
end

function s = feeder_sig(x)
sz = size(x); x = double(x(:));
if isempty(x), s = sprintf('sz=%s;n=0',mat2str(sz)); return; end
s = sprintf('sz=%s;n=%d;s1=%.16g;s2=%.16g;mn=%.16g;mx=%.16g', ...
    mat2str(sz),numel(x),sum(x),sum(x.^2),min(x),max(x));
end

function cache = feeder_compile_optimizer(data, rhoPQ)
N = data.N; T = data.T; B = data.B; L = data.L;

cPPar = sdpvar(N,T,'full');
cQPar = sdpvar(N,T,'full');
zPvar = sdpvar(N,T,'full');
zQvar = sdpvar(N,T,'full');
Pij   = sdpvar(L,T,'full');
Qij   = sdpvar(L,T,'full');
V     = sdpvar(B,T,'full');

F = [];
F = [F, V >= repmat(data.Vmin.^2,1,T), V <= repmat(data.Vmax.^2,1,T)];
F = [F, 0 <= zPvar, zPvar <= repmat(data.PgridMax,1,T)];
F = [F, zQvar >= repmat(data.QinjMin,1,T), zQvar <= repmat(data.QinjMax,1,T)];

Obj = 0;
for i = 1:N
    if isscalar(rhoPQ)
        rho_i = rhoPQ;
    else
        rho_i = rhoPQ(i);
    end
    for t = 1:T
        Obj = Obj + 0.5*rho_i*(zPvar(i,t)^2 + zQvar(i,t)^2) + cPPar(i,t)*zPvar(i,t) + cQPar(i,t)*zQvar(i,t);
    end
end

for t = 1:T
    F = [F, V(data.rootBus,t) == data.Vslack^2];

    for l = 1:L
        from = data.branch(l,1);
        to   = data.branch(l,2);

        Pchild = 0;
        Qchild = 0;
        child_lines = data.out_lines{to};
        for kk = 1:length(child_lines)
            lp = child_lines(kk);
            Pchild = Pchild + Pij(lp,t);
            Qchild = Qchild + Qij(lp,t);
        end

        Pload = data.PbusBase(to,t);
        Qload = data.QbusBase(to,t);

        if data.bus_has_comm(to)
            i = data.bus_to_comm(to);
            Pload = Pload + zPvar(i,t);
            Qload = Qload + zQvar(i,t);
        end

        F = [F, Pij(l,t) == Pchild + Pload, Qij(l,t) == Qchild + Qload];
        F = [F, V(to,t) == V(from,t) - 2*(data.rline(l)*(Pij(l,t)/data.baseMVA) + data.xline(l)*(Qij(l,t)/data.baseMVA))];
        F = [F, -data.PijMax(l) <= Pij(l,t), Pij(l,t) <= data.PijMax(l)];
        F = [F, -data.QijMax(l) <= Qij(l,t), Qij(l,t) <= data.QijMax(l)];
    end

    Psub = 0;
    rootOut = data.out_lines{data.rootBus};
    for kk = 1:length(rootOut)
        Psub = Psub + Pij(rootOut(kk),t);
    end
    F = [F, 0 <= Psub, Psub <= data.PsubMax(t)];
end

ops = sdpsettings('solver','gurobi','verbose',0,'warning',0,'cachesolvers',1);
paramVars = [cPPar(:); cQPar(:)];
wantedVec = [zPvar(:); zQvar(:); Pij(:); Qij(:); V(:)];
cache.opt = optimizer(F, Obj, ops, paramVars, wantedVec);
cache.N = N; cache.T = T; cache.B = B; cache.L = L;
end

function paramVec = feeder_pack_parameters(targetP, targetQ, rhoPQ)
[N,T] = size(targetP);
cP = zeros(N,T); cQ = zeros(N,T);
for i = 1:N
    if isscalar(rhoPQ)
        rho_i = rhoPQ;
    else
        rho_i = rhoPQ(i);
    end
    cP(i,:) = -rho_i*targetP(i,:);
    cQ(i,:) = -rho_i*targetQ(i,:);
end
paramVec = [cP(:); cQ(:)];
end

function [zP, zQ, feeder] = feeder_unpack_solution(solVec, cache)
N = cache.N; T = cache.T; B = cache.B; L = cache.L;
idx = 1;
zP = reshape(solVec(idx:idx+N*T-1), N, T); idx = idx + N*T;
zQ = reshape(solVec(idx:idx+N*T-1), N, T); idx = idx + N*T;
Pij = reshape(solVec(idx:idx+L*T-1), L, T); idx = idx + L*T;
Qij = reshape(solVec(idx:idx+L*T-1), L, T); idx = idx + L*T;
V   = reshape(solVec(idx:idx+B*T-1), B, T);
feeder = struct('Pij',Pij,'Qij',Qij,'V',V,'zP',zP,'zQ',zQ);
end
