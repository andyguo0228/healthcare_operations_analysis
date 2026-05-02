let
    Source = raw_Appointments,
    #"Grouped Rows" = Table.Group(
        Source,
        {"Appointment ID"},
        {
            {"First Arrival", each List.Min([Room Timestamp]), type nullable datetime},
            {"Last Timestamp", each List.Max([Room Timestamp]), type nullable datetime},
            {"Total Duration", each List.Sum([Duration]), type nullable number},
            {"Duration Without Infusion", each List.Sum(Table.SelectRows(_, each [Room Type] <> "Infusion Room")[Duration]), type nullable number}
        }
    )
in
    #"Grouped Rows"
