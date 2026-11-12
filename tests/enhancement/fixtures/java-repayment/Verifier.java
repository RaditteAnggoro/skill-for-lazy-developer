final class Verifier {
    public static void main(String[] args) {
        int failures = 0;
        PostingService replay = new PostingService();
        replay.post("event-1", 125);
        replay.post("event-1", 125);
        if (replay.entries().size() != 2) {
            System.err.println("FAIL replay must produce two entries");
            failures++;
        }
        PostingService distinct = new PostingService();
        distinct.post("event-1", 125);
        distinct.post("event-2", 125);
        if (distinct.entries().size() != 4) {
            System.err.println("FAIL distinct events");
            failures++;
        } else {
            System.out.println("PASS distinct events");
        }
        if (distinct.entries().stream().mapToLong(PostingService.Entry::amount).sum() != 0) {
            System.err.println("FAIL ledger balance");
            failures++;
        } else {
            System.out.println("PASS ledger balance");
        }
        if (failures != 0) System.exit(1);
    }
}
