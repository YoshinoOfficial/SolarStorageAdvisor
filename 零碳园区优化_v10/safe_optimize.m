% Safe optimize with solver fallback
function diagnostics = safe_optimize(F, Obj)
    fallback = {'gurobi','cplex','copt','mosek','xpress','scip','cbc','glpk','quadprog'};
    tried = {};

    primarySolver = pick_solver_local();
    if ~isempty(primarySolver)
        tried{end+1} = primarySolver;
        try
            ops = sdpsettings('solver', primarySolver, 'verbose', 0, 'warning', 0);
            diagnostics = optimize(F, Obj, ops);
            if diagnostics.problem == 0
                return;
            end
        catch
        end
    end

    for k = 1:numel(fallback)
        candidate = fallback{k};
        if any(strcmpi(tried, candidate))
            continue;
        end
        try
            ops = sdpsettings('solver', candidate, 'verbose', 0, 'warning', 0);
            diagnostics = optimize(F, Obj, ops);
            if diagnostics.problem == 0
                return;
            end
        catch
        end
    end

    ops = sdpsettings('verbose', 0, 'warning', 0);
    diagnostics = optimize(F, Obj, ops);
end

function solver = pick_solver_local()
    preferred = {'gurobi','cplex','copt','mosek','xpress','scip'};
    solver = '';
    for k = 1:numel(preferred)
        if exist(preferred{k},'file') || ~isempty(which(preferred{k}))
            solver = preferred{k};
            return;
        end
    end
    % YALMIP-based check
    try
        solvers = yalmip('solvers');
        for k = 1:numel(preferred)
            idx = find(strcmpi({solvers.tag}, preferred{k}), 1);
            if ~isempty(idx)
                solver = preferred{k};
                return;
            end
        end
    catch
    end
end
