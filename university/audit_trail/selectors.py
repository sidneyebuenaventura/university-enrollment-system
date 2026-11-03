from university.framework.events import EventObject


def actor_name_get(actor: EventObject = None) -> str:
    if not actor:
        return "System"

    first_name = actor.data.get("first_name")
    last_name = actor.data.get("last_name")

    if first_name and last_name:
        return f"{last_name}, {first_name}"

    username = actor.data.get("username")

    if username:
        return username

    return str(actor.data.get("id"))


def actor_type_get(actor: EventObject = None) -> str:
    if not actor:
        return "System"

    actor_obj = actor.get_from_db()

    if actor_obj:
        return actor_obj.type.label

    ctype = actor.get_ctype()
    return str(ctype)


def target_difference_get(old_target: EventObject, new_target: EventObject) -> dict:
    processed_fields = []
    data = {}

    for field, value in old_target.data.items():
        if field in processed_fields:
            continue

        if field not in new_target.data:
            # Removed
            data[field] = {"old": value, "new": None}
            processed_fields.append(field)
            continue

        new_value = new_target.data.get(field)

        # Changed
        if isinstance(value, list):
            old_list = set(value)
            new_list = set(new_value)

            removed = old_list - new_list
            added = new_list - old_list
            list_changes = {}

            if removed:
                list_changes["removed"] = list(removed)
            if added:
                list_changes["added"] = list(added)
            if list_changes:
                list_changes["old"] = list(old_list)
                list_changes["new"] = list(new_list)
                data[field] = list_changes
        elif value != new_value:
            data[field] = {"old": value, "new": new_target.data[field]}

        processed_fields.append(field)

    for field, value in new_target.data.items():
        if field in processed_fields:
            continue

        if field not in old_target.data:
            # Added
            data[field] = {"old": None, "new": value}

    return data
