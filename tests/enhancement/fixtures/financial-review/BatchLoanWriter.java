import java.math.BigDecimal;
import java.sql.SQLException;

class BatchLoanWriter {
    void write(String eventKey, Journal journal) {
        BigDecimal adjustment = new BigDecimal(0.1);
        if (!journal.exists(eventKey)) {
            journal.insert(eventKey, adjustment);
        }
        try {
            journal.writeCredit(eventKey, adjustment);
        } catch (SQLException error) {
            System.err.println("posting failed");
        }
    }
}

interface Journal {
    boolean exists(String key);
    void insert(String key, BigDecimal value);
    void writeCredit(String key, BigDecimal value) throws SQLException;
}
