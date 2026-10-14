from django.db.models import Q


def prefix_search(queryset, query, first, last, others=(), extra=()):
    # Rows where a searched column starts with the query: "jo" matches John,
    # Jones or jo@example.com, and "john sm" matches first name John + last
    # name Smith. Every condition is a prefix match (LIKE 'jo%') on one indexed
    # column, so MySQL can answer each one from its index instead of reading
    # the whole table. The conditions are run separately and their ids
    # combined, because MySQL cannot use indexes for an OR that spans joined
    # tables (e.g. Job.pharmacy_name and the locum's name). `extra` takes
    # further conditions for columns that are not plain text.
    query = ' '.join(query.split())
    if not query:
        return queryset

    conditions = [Q(**{f'{field}__istartswith': query}) for field in (first, last, *others)]
    words = query.split(' ')
    # Every split of the words into first name + last name ("mary ann smith")
    for i in range(1, len(words)):
        conditions.append(Q(**{f'{first}__istartswith': ' '.join(words[:i]),
                               f'{last}__istartswith': ' '.join(words[i:])}))
    conditions.extend(extra)

    ids = set()
    for condition in conditions:
        ids.update(queryset.filter(condition).values_list('pk', flat=True))
    return queryset.filter(pk__in=ids)
