"""Only allowed deterministic entry point for the Domain Skill."""
from .schemas import check_input
from .optimizer import greedy_schedule, bounded_beam_schedule
from .validators import structural_check


def schedule(dataset, strategy='deadline_scarcity'):
    check_input(dataset)
    if strategy == 'deadline_scarcity':
        output=greedy_schedule(dataset)
    elif strategy == 'bounded_beam':
        output=bounded_beam_schedule(dataset)
    else:
        raise ValueError('Unapproved skill strategy')
    structural_check(dataset,output)
    return output
