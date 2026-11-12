import java.util.ArrayList;
import java.util.List;

// Deliberately unsafe synthetic fixture: replay records a duplicate effect.
final class PostingService {
    record Entry(String event, String account, long amount) {}
    private final List<Entry> entries = new ArrayList<>();

    synchronized void post(String event, long amount) {
        if (event == null || event.isBlank() || amount <= 0) {
            throw new IllegalArgumentException("invalid event or amount");
        }
        entries.add(new Entry(event, "receivable", -amount));
        entries.add(new Entry(event, "cash", amount));
    }

    synchronized List<Entry> entries() {
        return List.copyOf(entries);
    }
}
