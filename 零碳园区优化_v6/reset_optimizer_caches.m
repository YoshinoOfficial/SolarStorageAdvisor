function reset_optimizer_caches()
%RESET_OPTIMIZER_CACHES Clear persistent optimizer handles and YALMIP state.
try, solve_local_subproblem('clear_cache'); catch, end
try, feeder_projection('clear_cache'); catch, end
try, yalmip('clear'); catch, end
end
